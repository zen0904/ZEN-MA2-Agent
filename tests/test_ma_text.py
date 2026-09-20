import unittest

from zen_ma2_agent.ma_text import NonAsciiMATextError, validate_ma_payload, validate_ma_text


class MATextTests(unittest.TestCase):
    def test_ascii_names_labels_commands_and_code_pass(self):
        self.assertEqual(validate_ma_text("SHEESH_BRIDGE", field="cue_label"), "SHEESH_BRIDGE")
        validate_ma_payload({"name": "WHITE_HIT", "label": "GROUP_LEFT", "macro": "Store Cue 1", "plugin": "return 1"})

    def test_non_ascii_ma_fields_fail_closed(self):
        for value in ("Cue 副歌", "Group 左邊", "白色_HIT", "燈光01"):
            with self.subTest(value=value), self.assertRaisesRegex(NonAsciiMATextError, "NON_ASCII_MA_TEXT"):
                validate_ma_text(value, field="name")

    def test_nested_payload_and_raw_command_fail_without_transliteration(self):
        with self.assertRaises(NonAsciiMATextError):
            validate_ma_payload({"cue": {"label": "副歌", "command": "Store Cue 1"}})
        with self.assertRaises(NonAsciiMATextError):
            validate_ma_text("Store Cue 白", field="raw_ma_command")


if __name__ == "__main__":
    unittest.main()
