import unittest

from zen_ma2_agent.state.providers.group_export import GroupExportParseError, group_membership_from_export


GROUP_EXPORT = """<?xml version="1.0" encoding="utf-8"?>
<MA xmlns="http://schemas.malighting.de/grandma2/xml/MA">
  <Info datetime="2026-08-29T08:56:20" showfile="sanitized" />
  <Group index="0" name="HYBRID">
    <Subfixtures>
      <Subfixture fix_id="101" />
      <Subfixture fix_id="1007" />
      <Subfixture fix_id="2" />
    </Subfixtures>
  </Group>
</MA>"""


class GroupExportParserTests(unittest.TestCase):
    def test_real_ma2_39_shape_extracts_ordered_sparse_fixture_ids(self):
        result = group_membership_from_export(GROUP_EXPORT, 1)
        self.assertEqual(result, {
            "group_no": 1,
            "name": "HYBRID",
            "fixtures": [101, 1007, 2],
            "fixture_refs": ["101", "1007", "2"],
            "source": "ma2_group_export_xml",
        })


    def test_subfixture_index_is_preserved_as_exact_reference(self):
        xml = GROUP_EXPORT.replace('fix_id="1007"', 'fix_id="1007" sub_index="2"')
        result = group_membership_from_export(xml, 1)
        self.assertEqual(result["fixtures"], [101, 1007, 2])
        self.assertEqual(result["fixture_refs"], ["101", "1007.2", "2"])
        with self.assertRaisesRegex(GroupExportParseError, "INVALID_SUB_INDEX"):
            group_membership_from_export(xml.replace('sub_index="2"', 'sub_index="bad"'), 1)

    def test_both_instances_of_same_root_are_not_collapsed(self):
        xml = """<MA><Group index="6" name="STROBE"><Subfixtures>
        <Subfixture fix_id="701" sub_index="1" />
        <Subfixture fix_id="701" sub_index="2" />
        <Subfixture fix_id="702" sub_index="1" />
        <Subfixture fix_id="702" sub_index="2" />
        </Subfixtures></Group></MA>"""
        result = group_membership_from_export(xml, 7)
        self.assertEqual(result["fixtures"], [701, 701, 702, 702])
        self.assertEqual(result["fixture_refs"], ["701.1", "701.2", "702.1", "702.2"])

    def test_default_namespace_and_zero_based_group_index_are_required(self):
        with self.assertRaisesRegex(GroupExportParseError, "GROUP_NUMBER_MISMATCH"):
            group_membership_from_export(GROUP_EXPORT, 2)

    def test_empty_subfixtures_is_a_valid_empty_group_not_missing_membership(self):
        xml = GROUP_EXPORT.replace('<Subfixture fix_id="101" />\n      <Subfixture fix_id="1007" />\n      <Subfixture fix_id="2" />', "")
        self.assertEqual(group_membership_from_export(xml, 1)["fixtures"], [])

    def test_empty_group_and_unknown_schema_are_distinguished(self):
        self.assertEqual(group_membership_from_export('<MA><Group index="0" name="Empty" /></MA>', 1)["fixtures"], [])
        with self.assertRaisesRegex(GroupExportParseError, "NO_MEMBERSHIP"):
            group_membership_from_export('<MA><Group index="0" name="HYBRID"><Selection /></Group></MA>', 1)

    def test_invalid_fixture_reference_is_not_invented(self):
        with self.assertRaisesRegex(GroupExportParseError, "INVALID_FIX_ID"):
            group_membership_from_export(GROUP_EXPORT.replace('fix_id="101"', 'fix_id="channel-101"'), 1)

    def test_malformed_export_is_rejected(self):
        with self.assertRaisesRegex(GroupExportParseError, "MALFORMED"):
            group_membership_from_export("<MA><Group>", 1)


if __name__ == "__main__":
    unittest.main()
