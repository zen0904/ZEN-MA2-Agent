import socket
import unittest

from zen_ma2_agent.ma_bridge.server import BridgeDispatcher, BridgeServer


class BridgeDispatcherTests(unittest.TestCase):
    def test_ping_status_and_parse_only_commands(self):
        dispatcher = BridgeDispatcher(lambda: "FIELD_CORE_AVAILABLE=YES REMOTE_AI_AVAILABLE=NO")
        self.assertEqual(dispatcher.handle_line("ZEN/1 REQ 1 PING"), "ZEN/1 READY 1 PONG")
        self.assertEqual(
            dispatcher.handle_line("ZEN/1 REQ 2 STATUS"),
            "ZEN/1 READY 2 FIELD_CORE_AVAILABLE=YES REMOTE_AI_AVAILABLE=NO",
        )
        self.assertEqual(
            dispatcher.handle_line("ZEN/1 REQ 3 DIMMER GROUP=4 VALUE=50"),
            "ZEN/1 READY 3 NOT_EXECUTED",
        )
        self.assertEqual(
            dispatcher.handle_line("ZEN/1 REQ 4 DESIGN REQUEST=NEXT_SECTION"),
            "ZEN/1 READY 4 NOT_IMPLEMENTED",
        )

    def test_duplicate_request_returns_original_response(self):
        calls = []

        def status():
            calls.append(1)
            return f"COUNT={len(calls)}"

        dispatcher = BridgeDispatcher(status)
        first = dispatcher.handle_line("ZEN/1 REQ abc STATUS")
        second = dispatcher.handle_line("ZEN/1 REQ abc STATUS")
        self.assertEqual(first, "ZEN/1 READY abc COUNT=1")
        self.assertEqual(second, first)
        self.assertEqual(len(calls), 1)

    def test_conflicting_request_id_is_rejected(self):
        dispatcher = BridgeDispatcher()
        dispatcher.handle_line("ZEN/1 REQ same PING")
        self.assertEqual(
            dispatcher.handle_line("ZEN/1 REQ same STATUS"),
            "ZEN/1 ERROR same REQUEST_ID_CONFLICT",
        )

    def test_invalid_line_fails_closed(self):
        dispatcher = BridgeDispatcher()
        self.assertEqual(
            dispatcher.handle_line("ZEN/9 REQ x PING"),
            "ZEN/1 ERROR x INVALID_PROTOCOL",
        )


class BridgeTcpServerTests(unittest.TestCase):
    def test_loopback_tcp_roundtrip(self):
        server = BridgeServer(host="127.0.0.1", port=0)
        server.start()
        try:
            with socket.create_connection((server.host, server.port), timeout=2.0) as sock:
                sock.sendall(b"ZEN/1 REQ tcp1 PING\n")
                response = sock.makefile("rb").readline().decode("utf-8").strip()
            self.assertEqual(response, "ZEN/1 READY tcp1 PONG")
        finally:
            server.stop()

    def test_non_loopback_is_blocked_by_default(self):
        with self.assertRaises(ValueError):
            BridgeServer(host="0.0.0.0")


if __name__ == "__main__":
    unittest.main()
