from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zen_ma2_agent.llm.autonomous_designer import SCHEMA, DesignValidationError, validate_design_output
from zen_ma2_agent.llm.router import ProviderRouter, ProviderSlot, ProviderUnavailable, load_provider_slots
from zen_ma2_agent.config import settings_path


class _Adapter:
    def __init__(self, responses: dict[int, object]): self.responses = responses
    def complete(self, slot, *, system, user):
        value = self.responses[slot.number]
        if isinstance(value, Exception): raise value
        return value


class PortableLLMRouterTests(unittest.TestCase):
    def test_three_slots_and_fallback_do_not_expose_key(self):
        slots = tuple(ProviderSlot(i, "OPENAI_COMPATIBLE", "m", "https://example.test/v1", "secret", ("DESIGNER",), 10) for i in range(1, 4))
        router = ProviderRouter("FALLBACK", slots, _Adapter({1: ProviderUnavailable("down"), 2: "{}", 3: "never"}))
        content, chosen = router.complete(role="DESIGNER", system="s", user="u")
        self.assertEqual(content, "{}")
        self.assertEqual(chosen.number, 2)
        self.assertNotIn("secret", json.dumps(chosen.safe_identity()))

    def test_private_env_loads_three_slots(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "providers.private.env"
            path.write_text("ZEN_PROVIDER_MODE=ROUTED\nZEN_PROVIDER_1_TYPE=OPENAI_COMPATIBLE\nZEN_PROVIDER_1_MODEL=test\nZEN_PROVIDER_1_BASE_URL=https://example.test/v1\nZEN_PROVIDER_1_API_KEY=key\nZEN_PROVIDER_1_ROLES=DESIGNER\n", encoding="utf-8")
            mode, slots = load_provider_slots(path)
        self.assertEqual(mode, "ROUTED")
        self.assertTrue(slots[0].configured)
        self.assertFalse(slots[1].configured)

    def test_design_rejects_raw_command_fields(self):
        output = {key: {} for key in ("design_intent", "visual_strategy", "virtual_rig", "position_vocabulary", "main_sequence", "free_cue_layer", "evidence_trace")}
        output |= {"schema": SCHEMA, "ma2_commands": ["Store Sequence 1"]}
        with self.assertRaises(DesignValidationError):
            validate_design_output(output)

    def test_design_requires_structured_fields(self):
        with self.assertRaises(DesignValidationError):
            validate_design_output({"schema": SCHEMA})

    def test_zen_home_redirects_preferences_outside_repository(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"ZEN_HOME": temp}, clear=False):
            self.assertEqual(settings_path(), Path(temp) / "config" / "settings.json")
