import unittest

from zen_ma2_agent.ma2_gui_navigation import (
    MA2GuiNavigationError,
    MA2Screen,
    MA2StageViewNavigationService,
    NavigationDispatch,
    WindowsMA2ScreenNavigator,
)


def _observation(*, stage: bool, digest: str = "a" * 64):
    return {
        "schema": "zen.ma2_visual_observation.v0.1",
        "stage_view_visible": stage,
        "capture_readable": True,
        "image": {"sha256": digest},
        "ma2_writes": 0,
    }


class _Navigator:
    def __init__(self, *, fail_on: int | None = None):
        self.calls = []
        self.fail_on = fail_on

    def show_screen(self, screen: MA2Screen):
        self.calls.append(int(screen))
        if int(screen) == self.fail_on:
            raise MA2GuiNavigationError("FAIL_CLOSED_TEST_BLOCKER")
        return NavigationDispatch(
            screen=int(screen),
            method="HWND_VERIFIED_SCREEN_BUTTON",
            status="SENT",
        )


class _Observations:
    def __init__(self, values):
        self.values = list(values)
        self.calls = 0

    def __call__(self):
        value = self.values[min(self.calls, len(self.values) - 1)]
        self.calls += 1
        return value


class MA2GuiNavigationTests(unittest.TestCase):
    def test_already_visible_never_sends_gui_input(self):
        navigator = _Navigator()
        service = MA2StageViewNavigationService(
            navigator,
            _Observations([_observation(stage=True)]),
        )
        result = service.navigate_and_observe()
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["write_authority"], "NONE")
        self.assertEqual(result["ma2_show_writes"], 0)
        self.assertEqual(result["attempts"], [])
        self.assertEqual(navigator.calls, [])

    def test_stops_after_stage_view_is_verified(self):
        navigator = _Navigator()
        service = MA2StageViewNavigationService(
            navigator,
            _Observations(
                [
                    _observation(stage=False, digest="a" * 64),
                    _observation(stage=False, digest="b" * 64),
                    _observation(stage=True, digest="c" * 64),
                ]
            ),
        )
        result = service.navigate_and_observe()
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(navigator.calls, [2, 3])
        self.assertTrue(result["observation"]["stage_view_visible"])
        self.assertEqual(result["ma2_show_writes"], 0)

    def test_existing_native_screen_is_captured_before_any_gui_input(self):
        navigator = _Navigator()
        seen = []

        def candidate(title):
            seen.append(title)
            return _observation(
                stage=title == "Screen 6",
                digest=("f" if title == "Screen 6" else "b") * 64,
            )

        service = MA2StageViewNavigationService(
            navigator,
            _Observations([_observation(stage=False)]),
            candidate_observation_provider=candidate,
        )
        result = service.navigate_and_observe()
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(seen, ["Screen 6"])
        self.assertEqual(navigator.calls, [])
        self.assertEqual(service.observation_provider.calls, 0)
        self.assertTrue(result["observation"]["stage_view_visible"])
        self.assertEqual(result["ma2_show_writes"], 0)

    def test_navigation_failure_returns_blocked_without_retrying_other_screens(self):
        navigator = _Navigator(fail_on=2)
        service = MA2StageViewNavigationService(
            navigator,
            _Observations([_observation(stage=False)]),
        )
        result = service.navigate_and_observe()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["failure"]["code"], "GUI_NAVIGATION_FAIL_CLOSED")
        self.assertEqual(navigator.calls, [2])
        self.assertEqual(result["ma2_show_writes"], 0)

    def test_no_stage_view_on_allowed_screens_is_blocked(self):
        navigator = _Navigator()
        service = MA2StageViewNavigationService(
            navigator,
            _Observations([_observation(stage=False)] * 4),
        )
        result = service.navigate_and_observe()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["failure"]["code"],
            "STAGE_VIEW_NOT_FOUND_ON_ALLOWED_SCREENS",
        )
        self.assertEqual(navigator.calls, [2, 3, 4])
        self.assertEqual(result["ma2_show_writes"], 0)

    def test_visual_path_with_any_write_count_fails_closed(self):
        service = MA2StageViewNavigationService(
            _Navigator(),
            _Observations(
                [
                    {
                        "schema": "zen.ma2_visual_observation.v0.1",
                        "stage_view_visible": False,
                        "ma2_writes": 1,
                    }
                ]
            ),
        )
        with self.assertRaisesRegex(MA2GuiNavigationError, "REPORTED_MA2_WRITES"):
            service.navigate_and_observe()

    def test_public_driver_rejects_non_screen_enum(self):
        navigator = WindowsMA2ScreenNavigator()
        with self.assertRaisesRegex(MA2GuiNavigationError, "Only Screen 2"):
            navigator.show_screen(1)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
