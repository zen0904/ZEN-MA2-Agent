import unittest
from types import SimpleNamespace

from zen_ma2_agent.host_metrics import HostMetricsProvider


class _FakePsutil:
    @staticmethod
    def cpu_percent(interval=None):
        return 23.456

    @staticmethod
    def virtual_memory():
        return SimpleNamespace(
            percent=61.2,
            available=4 * 1024 * 1024 * 1024,
            total=8 * 1024 * 1024 * 1024,
        )

    @staticmethod
    def disk_usage(path):
        return SimpleNamespace(
            percent=72.3,
            free=50 * 1024 * 1024 * 1024,
            total=200 * 1024 * 1024 * 1024,
        )

    @staticmethod
    def sensors_temperatures():
        return {
            "cpu": [
                SimpleNamespace(current=55.0),
                SimpleNamespace(current=62.5),
            ]
        }


class HostMetricsTests(unittest.TestCase):
    def test_collects_existing_psutil_metrics(self):
        data = HostMetricsProvider(
            disk_path="/",
            psutil_module=_FakePsutil,
        ).snapshot()
        self.assertEqual(data["schema"], "zen.host_status.v0.1")
        self.assertEqual(data["state"], "ONLINE")
        self.assertEqual(data["cpu_percent"], 23.46)
        self.assertEqual(data["memory"]["percent"], 61.2)
        self.assertEqual(data["memory"]["available_mb"], 4096)
        self.assertEqual(data["disk"]["percent"], 72.3)
        self.assertEqual(data["temperature_c"], 62.5)
        self.assertEqual(data["errors"], [])

    def test_temperature_unavailable_is_not_failure(self):
        class NoTemperature(_FakePsutil):
            sensors_temperatures = None

        data = HostMetricsProvider(
            disk_path="/",
            psutil_module=NoTemperature,
        ).snapshot()
        self.assertEqual(data["state"], "ONLINE")
        self.assertIsNone(data["temperature_c"])

    def test_core_metric_failure_is_degraded_not_exception(self):
        class Broken(_FakePsutil):
            @staticmethod
            def virtual_memory():
                raise OSError("metric unavailable")

        data = HostMetricsProvider(
            disk_path="/",
            psutil_module=Broken,
        ).snapshot()
        self.assertEqual(data["state"], "DEGRADED")
        self.assertIsNone(data["memory"]["percent"])
        self.assertTrue(any(item.startswith("memory:") for item in data["errors"]))

    def test_missing_psutil_is_degraded(self):
        data = HostMetricsProvider(
            disk_path="/",
            psutil_module=None,
        )
        data._psutil = None
        snapshot = data.snapshot()
        self.assertEqual(snapshot["state"], "DEGRADED")
        self.assertIn("psutil unavailable", snapshot["errors"])


if __name__ == "__main__":
    unittest.main()
