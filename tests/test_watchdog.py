import time
import unittest

from zen_ma2_agent.operator_api import ComponentState
from zen_ma2_agent.watchdog import (
    WatchdogComponent,
    WatchdogMonitor,
    WatchdogService,
)


class WatchdogTests(unittest.TestCase):
    def test_initial_healthy_observation_is_quiet(self):
        monitor = WatchdogMonitor()
        events = monitor.observe(
            (WatchdogComponent("field_core", ComponentState.ONLINE, required=True),)
        )
        self.assertEqual(events, ())
        self.assertEqual(monitor.snapshot()["state"], "ONLINE")

    def test_required_offline_is_critical_and_edge_triggered(self):
        monitor = WatchdogMonitor()
        events = monitor.observe(
            (
                WatchdogComponent(
                    "ma_bridge",
                    ComponentState.OFFLINE,
                    required=True,
                    detail="bridge process not running",
                ),
            )
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].severity.value, "CRITICAL")
        self.assertEqual(monitor.snapshot()["state"], "OFFLINE")

        repeated = monitor.observe(
            (
                WatchdogComponent(
                    "ma_bridge",
                    ComponentState.OFFLINE,
                    required=True,
                    detail="bridge process not running",
                ),
            )
        )
        self.assertEqual(repeated, ())
        self.assertEqual(len(monitor.snapshot()["recent_events"]), 1)

    def test_optional_worker_offline_is_warning_not_field_failure(self):
        monitor = WatchdogMonitor()
        events = monitor.observe(
            (
                WatchdogComponent("field_core", ComponentState.ONLINE, required=True),
                WatchdogComponent("worker-a", ComponentState.OFFLINE, required=False),
            )
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].severity.value, "WARNING")
        self.assertEqual(monitor.snapshot()["state"], "DEGRADED")

    def test_recovery_generates_info_event(self):
        monitor = WatchdogMonitor()
        monitor.observe(
            (WatchdogComponent("worker-a", ComponentState.OFFLINE, required=False),)
        )
        events = monitor.observe(
            (WatchdogComponent("worker-a", ComponentState.ONLINE, required=False),)
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].severity.value, "INFO")
        self.assertEqual(events[0].previous_state.value, "OFFLINE")
        self.assertEqual(events[0].current_state.value, "ONLINE")

    def test_unknown_is_preserved_without_alert_spam(self):
        monitor = WatchdogMonitor()
        events = monitor.observe(
            (WatchdogComponent("worker-b", ComponentState.UNKNOWN),)
        )
        self.assertEqual(events, ())
        self.assertEqual(monitor.snapshot()["state"], "UNKNOWN")

    def test_duplicate_component_is_rejected(self):
        monitor = WatchdogMonitor()
        with self.assertRaises(ValueError):
            monitor.observe(
                (
                    WatchdogComponent("worker-a", ComponentState.ONLINE),
                    WatchdogComponent("worker-a", ComponentState.OFFLINE),
                )
            )

    def test_event_queue_is_bounded(self):
        monitor = WatchdogMonitor(event_capacity=2)
        monitor.observe((WatchdogComponent("x", ComponentState.OFFLINE),))
        monitor.observe((WatchdogComponent("x", ComponentState.ONLINE),))
        monitor.observe((WatchdogComponent("x", ComponentState.OFFLINE),))
        events = monitor.snapshot()["recent_events"]
        self.assertEqual(len(events), 2)
        self.assertEqual([item["sequence"] for item in events], [2, 3])

    def test_service_polling_is_independent_and_stoppable(self):
        state = {"value": ComponentState.ONLINE}

        def provider():
            return (WatchdogComponent("field_core", state["value"], required=True),)

        service = WatchdogService(
            WatchdogMonitor(),
            provider,
            interval_seconds=0.01,
        )
        service.start()
        self.assertTrue(service.running)
        state["value"] = ComponentState.OFFLINE
        time.sleep(0.04)
        service.stop()
        self.assertFalse(service.running)
        snapshot = service.snapshot()
        self.assertEqual(snapshot["state"], "OFFLINE")
        self.assertEqual(snapshot["recent_events"][-1]["severity"], "CRITICAL")


if __name__ == "__main__":
    unittest.main()
