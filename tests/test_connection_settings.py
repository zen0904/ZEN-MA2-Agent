import json
import socket
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.config import SettingsError, load_preferences, save_preferences, settings_path, validate_ma2_settings, validate_state_adapter_settings
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState, MA2TelnetClient, login_command, strip_ansi


class FakeRuntimeClient:
    instances = []

    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.connect_args = None
        FakeRuntimeClient.instances.append(self)

    def connect(self, username, password=""):
        self.connect_args = (username, password)
        self.authenticated_user = "administrator"
        self.state = ConnectionState.READY
        return "Logged in as User 'administrator'"

    def execute(self, command):
        return f"sent: {command}"

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class FakeSocket:
    def __init__(self, login_responses=None):
        self.sent = []
        self.login_responses = list(login_responses or [])
        self.responses = []
        self.closed = False

    def settimeout(self, _timeout):
        pass

    def sendall(self, value):
        self.sent.append(value)
        if value.startswith(b"Login"):
            self.responses.extend(self.login_responses)

    def recv(self, _size):
        if self.responses:
            return self.responses.pop(0)
        raise socket.timeout()

    def shutdown(self, _how):
        pass

    def close(self):
        self.closed = True


class ConnectionSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-ma2-test-")
        self.root = Path(self.temp.name)
        FakeRuntimeClient.instances = []

    def tearDown(self):
        self.temp.cleanup()

    def runtime(self):
        return AgentRuntime(self.root, client_factory=FakeRuntimeClient)

    def poll_until_settled(self, client, limit=0.2):
        import time
        end = time.monotonic() + limit
        while time.monotonic() < end and client.state is ConnectionState.AUTHENTICATING:
            time.sleep(0.01)
            client.poll_authentication()

    def test_custom_host_port_username_and_blank_password(self):
        runtime = self.runtime()
        runtime.connect("ma2-console.local", "30001", "ShowUser", "")
        client = FakeRuntimeClient.instances[-1]
        self.assertEqual((client.host, client.port), ("ma2-console.local", 30001))
        self.assertEqual(client.connect_args, ("ShowUser", ""))
        self.assertIn("User: administrator", runtime.status_text())

    def test_password_never_written_and_settings_reload(self):
        runtime = self.runtime()
        runtime.connect("10.0.0.20", 30002, "MM", "not-for-json")
        text = settings_path(self.root).read_text(encoding="utf-8")
        self.assertNotIn("not-for-json", text)
        self.assertNotIn("password", text.lower())
        reloaded = load_preferences(self.root)
        self.assertEqual(reloaded["ma2"], {"host": "10.0.0.20", "port": 30002, "username": "MM"})

    def test_invalid_port_and_empty_username_block_authentication(self):
        with self.assertRaises(SettingsError):
            validate_ma2_settings("127.0.0.1", 0, "User")
        runtime = self.runtime()
        with self.assertRaises(SettingsError) as error:
            runtime.connect("127.0.0.1", 30000, "", "")
        self.assertEqual(str(error.exception), "USERNAME REQUIRED")
        self.assertEqual(FakeRuntimeClient.instances, [])

    def test_settings_changed_requires_reconnect_and_disconnect_disables_execute(self):
        runtime = self.runtime()
        runtime.connect("127.0.0.1", 30000, "User", "")
        runtime.preview("Go Sequence 5")
        self.assertTrue(runtime.ready)
        runtime.update_connection_settings("127.0.0.2", 30000, "User")
        self.assertTrue(runtime.reconnect_required)
        self.assertEqual(runtime.status_text(), "Settings changed — reconnect required")
        runtime.disconnect()
        self.assertEqual(runtime.state, ConnectionState.DISCONNECTED)
        self.assertIsNone(runtime.current_plan)
        with self.assertRaises(ConnectionError):
            runtime.execute_current()

    def test_requested_mm_guest_is_not_ready_then_mm_is_ready(self):
        fake_socket = FakeSocket([b"Login MM secret\r\nLogged in as User 'guest'\r\n"])
        client = MA2TelnetClient("localhost", 30000, auth_timeout_seconds=1, socket_factory=lambda *_args, **_kwargs: fake_socket)
        client.connect("MM", "")
        self.poll_until_settled(client, 0.05)
        self.assertEqual(client.state, ConnectionState.AUTHENTICATING)
        self.assertEqual(client.current_session_user, "guest")
        with self.assertRaises(Exception):
            client.execute("Go Sequence 5")
        fake_socket.responses.append(b"Logged in as User 'MM'\r\n")
        self.poll_until_settled(client)
        self.assertEqual(client.state, ConnectionState.READY)
        self.assertEqual(client.authenticated_user, "MM")
        self.assertEqual(fake_socket.sent[0], b"Login MM\r\n")
        self.assertIn("TX: Login MM", client.audit_entries)
        self.assertIn("RX: Logged in as User 'guest'", client.audit_entries)
        self.assertIn("RX: Logged in as User 'MM'", client.audit_entries)
        self.assertNotIn("secret", "\n".join(client.audit_entries))
        self.assertIn("RX: Login MM [REDACTED]", client.audit_entries)
        client.close()

    def test_requested_guest_can_be_ready_and_administrator_cannot_use_guest(self):
        guest_socket = FakeSocket([b"Logged in as User 'guest'\r\n"])
        guest = MA2TelnetClient("localhost", 30000, socket_factory=lambda *_args, **_kwargs: guest_socket)
        guest.connect("guest", "")
        self.poll_until_settled(guest)
        self.assertEqual(guest.state, ConnectionState.READY)
        admin_socket = FakeSocket([b"Logged in as User 'guest'\r\n"])
        admin = MA2TelnetClient("localhost", 30000, auth_timeout_seconds=1, socket_factory=lambda *_args, **_kwargs: admin_socket)
        admin.connect("administrator", "")
        self.poll_until_settled(admin, 0.05)
        self.assertEqual(admin.state, ConnectionState.AUTHENTICATING)
        self.assertNotEqual(admin.state, ConnectionState.READY)
        guest.close(); admin.close()

    def test_auth_timeout_crlf_ansi_and_reconnect_uses_new_username(self):
        fake_socket = FakeSocket([b"\x1b[32mLogged in as User 'guest'\x1b[0m\r\n"])
        sockets = [fake_socket, FakeSocket([b"Logged in as User 'administrator'\r\n"])]
        client = MA2TelnetClient("localhost", 30000, auth_timeout_seconds=0.01, socket_factory=lambda *_args, **_kwargs: sockets.pop(0))
        client.connect("MM", "secret")
        self.poll_until_settled(client)
        self.assertEqual(login_command("MM", ""), "Login MM")
        self.assertEqual(login_command("MM", "secret"), "Login MM secret")
        self.assertEqual(fake_socket.sent[0], b"Login MM secret\r\n")
        self.assertEqual(strip_ansi("\x1b[31mready\x1b[0m"), "ready")
        self.assertEqual(client.state, ConnectionState.AUTH_FAILED)
        self.assertEqual(client.current_session_user, "guest")
        client.close()
        client.connect("administrator", "")
        self.poll_until_settled(client)
        self.assertEqual(client.state, ConnectionState.READY)
        self.assertEqual(client.authenticated_user, "administrator")
        self.assertEqual(client.requested_username, "administrator")
        self.assertEqual(client.socket.sent[0], b"Login administrator\r\n")
        client.close()
        self.assertEqual(client.state, ConnectionState.DISCONNECTED)
        self.assertTrue(fake_socket.closed)

    def test_save_strips_untrusted_password_key(self):
        save_preferences({"ma2": {"host": "127.0.0.1", "port": 30000, "username": "User", "password": "bad"}}, self.root)
        saved = json.loads(settings_path(self.root).read_text(encoding="utf-8"))
        self.assertNotIn("password", json.dumps(saved).lower())

    def test_importexport_path_setting_accepts_auto_or_an_absolute_override(self):
        self.assertEqual(validate_state_adapter_settings({"plugin_slot": 375, "importexport_path": "auto"})["importexport_path"], "auto")
        override = r"C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\importexport"
        self.assertEqual(validate_state_adapter_settings({"importexport_path": override})["importexport_path"], override)
        with self.assertRaises(SettingsError):
            validate_state_adapter_settings({"importexport_path": "relative/importexport"})


if __name__ == "__main__":
    unittest.main()
