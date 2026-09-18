import unittest
from unittest.mock import patch

from scripts.host_preflight import ProbeTarget, _parse_target, collect


class HostPreflightTests(unittest.TestCase):
    def test_parse_target(self):
        target = _parse_target("ma=10.0.0.233:30000")
        self.assertEqual(target, ProbeTarget("ma", "10.0.0.233", 30000))

    def test_parse_target_rejects_invalid_value(self):
        for value in ("ma", "ma=", "ma=host", "ma=host:0", "ma=host:70000"):
            with self.subTest(value=value):
                with self.assertRaises(Exception):
                    _parse_target(value)

    @patch("scripts.host_preflight._probe")
    def test_collect_is_read_only_and_reports_zero_writes(self, probe):
        probe.return_value = {
            "name": "ma",
            "host": "127.0.0.1",
            "port": 30000,
            "reachable": False,
            "error": "test",
        }
        payload = collect((ProbeTarget("ma", "127.0.0.1", 30000),), 0.1)
        self.assertEqual(payload["schema"], "zen.host_preflight.v0.1")
        self.assertEqual(payload["ma2_writes"], 0)
        self.assertIn("service_manager", payload)
        self.assertIn("interfaces", payload)
        self.assertIn("packages", payload)
        self.assertEqual(len(payload["targets"]), 1)


if __name__ == "__main__":
    unittest.main()
