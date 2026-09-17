import unittest

from zen_ma2_agent.ma_bridge.protocol import (
    BridgeCommand,
    BridgeProtocolError,
    RequestDeduplicator,
    format_error,
    format_ready,
    parse_request_line,
)


class MABridgeProtocolTests(unittest.TestCase):
    def test_ping(self):
        request = parse_request_line("ZEN/1 REQ 1001 PING")
        self.assertEqual(request.command, BridgeCommand.PING)
        self.assertEqual(request.arguments, {})

    def test_status(self):
        request = parse_request_line("ZEN/1 REQ req-2 STATUS")
        self.assertEqual(request.command, BridgeCommand.STATUS)
        self.assertEqual(request.arguments, {})

    def test_dimmer(self):
        request = parse_request_line("ZEN/1 REQ 1003 DIMMER GROUP=4 VALUE=50")
        self.assertEqual(request.arguments, {"GROUP": 4, "VALUE": 50})

    def test_dimmer_fractional_value(self):
        request = parse_request_line("ZEN/1 REQ 1003a DIMMER GROUP=4 VALUE=12.5")
        self.assertEqual(request.arguments["VALUE"], 12.5)

    def test_design(self):
        request = parse_request_line("ZEN/1 REQ 1004 DESIGN REQUEST=NEXT_SECTION")
        self.assertEqual(request.arguments, {"REQUEST": "NEXT_SECTION"})

    def test_hash_is_stable_for_same_request(self):
        one = parse_request_line("ZEN/1 REQ 1003 DIMMER GROUP=4 VALUE=50")
        two = parse_request_line("ZEN/1 REQ 1003 DIMMER VALUE=50 GROUP=4")
        self.assertEqual(one.payload_hash, two.payload_hash)

    def test_unknown_protocol_is_rejected(self):
        with self.assertRaises(BridgeProtocolError) as caught:
            parse_request_line("ZEN/2 REQ 1001 PING")
        self.assertEqual(caught.exception.code, "INVALID_PROTOCOL")

    def test_unknown_command_is_rejected(self):
        with self.assertRaises(BridgeProtocolError) as caught:
            parse_request_line("ZEN/1 REQ 1001 SHELL")
        self.assertEqual(caught.exception.code, "UNKNOWN_COMMAND")

    def test_control_character_is_rejected(self):
        with self.assertRaises(BridgeProtocolError) as caught:
            parse_request_line("ZEN/1 REQ 1001 PING\n")
        self.assertEqual(caught.exception.code, "CONTROL_CHARACTER")

    def test_duplicate_argument_is_rejected(self):
        with self.assertRaises(BridgeProtocolError) as caught:
            parse_request_line("ZEN/1 REQ 1003 DIMMER GROUP=4 GROUP=5 VALUE=50")
        self.assertEqual(caught.exception.code, "DUPLICATE_ARGUMENT")

    def test_missing_argument_is_rejected(self):
        with self.assertRaises(BridgeProtocolError) as caught:
            parse_request_line("ZEN/1 REQ 1003 DIMMER GROUP=4")
        self.assertEqual(caught.exception.code, "MISSING_ARGUMENT")

    def test_dimmer_bounds_are_enforced(self):
        for value in ("-1", "101"):
            with self.subTest(value=value):
                with self.assertRaises(BridgeProtocolError) as caught:
                    parse_request_line(f"ZEN/1 REQ 1003 DIMMER GROUP=4 VALUE={value}")
                self.assertEqual(caught.exception.code, "INVALID_ARGUMENT")

    def test_design_rejects_shell_like_payload(self):
        with self.assertRaises(BridgeProtocolError) as caught:
            parse_request_line("ZEN/1 REQ 1004 DESIGN REQUEST=NEXT;rm")
        self.assertEqual(caught.exception.code, "INVALID_ARGUMENT")

    def test_ready_and_error_format(self):
        self.assertEqual(format_ready("1001", "PONG"), "ZEN/1 READY 1001 PONG")
        self.assertEqual(
            format_error("1001", "INVALID_ARGUMENT"),
            "ZEN/1 ERROR 1001 INVALID_ARGUMENT",
        )

    def test_dedup_same_payload(self):
        request = parse_request_line("ZEN/1 REQ 1001 PING")
        dedup = RequestDeduplicator(capacity=2)
        self.assertEqual(dedup.check(request), "NEW")
        self.assertEqual(dedup.check(request), "DUPLICATE")
        self.assertEqual(len(dedup), 1)

    def test_dedup_conflicting_payload(self):
        dedup = RequestDeduplicator()
        dedup.check(parse_request_line("ZEN/1 REQ same PING"))
        with self.assertRaises(BridgeProtocolError) as caught:
            dedup.check(parse_request_line("ZEN/1 REQ same STATUS"))
        self.assertEqual(caught.exception.code, "REQUEST_ID_CONFLICT")

    def test_dedup_is_bounded(self):
        dedup = RequestDeduplicator(capacity=2)
        dedup.check(parse_request_line("ZEN/1 REQ a PING"))
        dedup.check(parse_request_line("ZEN/1 REQ b PING"))
        dedup.check(parse_request_line("ZEN/1 REQ c PING"))
        self.assertEqual(len(dedup), 2)
        self.assertEqual(dedup.check(parse_request_line("ZEN/1 REQ a PING")), "NEW")


if __name__ == "__main__":
    unittest.main()
