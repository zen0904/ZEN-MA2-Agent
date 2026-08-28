import json
import socket
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.config import SettingsError, load_preferences, save_preferences, settings_path, validate_ma2_settings
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
    def __init__(self):
        self.sent = []
        self.responses = []
        self.closed = False

    def settimeout(self, _timeout):
        pass

    def sendall(self, value):
        self.sent.append(value)
        if value.startswith(b"Login"):
            self.responses.append(b"\x1b[32mLogged in as User 'administrator'\x1b[0m\r\n")

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

    def test_login_format_ansi_crlf_and_client_state_machine(self):
        fake_socket = FakeSocket()
        client = MA2TelnetClient("localhost", 30000, read_timeout_seconds=0.03, socket_factory=lambda *_args, **_kwargs: fake_socket)
        response = client.connect("MM", "secret")
        self.assertEqual(login_command("MM", ""), "Login MM")
        self.assertEqual(login_command("MM", "secret"), "Login MM secret")
        self.assertEqual(fake_socket.sent[0], b"Login MM secret\r\n")
        self.assertEqual(strip_ansi("\x1b[31mready\x1b[0m"), "ready")
        self.assertIn("Logged in as User 'administrator'", response)
        self.assertEqual(client.state, ConnectionState.READY)
        self.assertEqual(client.authenticated_user, "administrator")
        client.close()
        self.assertEqual(client.state, ConnectionState.DISCONNECTED)
        self.assertTrue(fake_socket.closed)

    def test_save_strips_untrusted_password_key(self):
        save_preferences({"ma2": {"host": "127.0.0.1", "port": 30000, "username": "User", "password": "bad"}}, self.root)
        saved = json.loads(settings_path(self.root).read_text(encoding="utf-8"))
        self.assertNotIn("password", json.dumps(saved).lower())


if __name__ == "__main__":
    unittest.main()
