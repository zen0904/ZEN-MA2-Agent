import os
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path

from zen_ma2_agent.state.providers.layouts import LayoutExportProvider
from zen_ma2_agent.state.providers.group_membership import (
    ExportFileGroupMembershipProvider,
    GroupMembershipProviderError,
    GroupMembershipProviderUnavailable,
    ImportExportPathResolver,
)


def group_xml(*fixture_ids: int, index: int = 0, name: str = "HYBRID", include_subfixtures: bool = True) -> str:
    subfixtures = "" if not include_subfixtures else "<Subfixtures>" + "".join(f'<Subfixture fix_id="{fixture_id}" />' for fixture_id in fixture_ids) + "</Subfixtures>"
    return f'<MA xmlns="http://schemas.malighting.de/grandma2/xml/MA"><Group index="{index}" name="{name}">{subfixtures}</Group></MA>'


class ExportRuntime:
    def __init__(self, directory: Path, *, host: str = "127.0.0.1", xml_factory=group_xml):
        self.preferences = {"ma2": {"host": host}}
        self.directory = directory
        self.root = directory
        self.xml_factory = xml_factory
        self.commands: list[tuple[int, str]] = []
        self.log_records: list[tuple[str, dict]] = []

    def export_group_file(self, group_no: int, filename: str) -> str:
        self.commands.append((group_no, filename))
        (self.directory / filename).write_text(self.xml_factory(101, 1007, 2, index=group_no - 1), encoding="utf-8")
        return "exported"

    def log(self, event: str, data: dict) -> None:
        self.log_records.append((event, data))


class GroupMembershipExportProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-group-export-")
        self.directory = Path(self.temp.name)
        self.settings = {"importexport_path": str(self.directory), "timeout_seconds": 1.0}

    def tearDown(self):
        self.temp.cleanup()

    def provider(self, request_id_factory=lambda: "request0001", **kwargs):
        return ExportFileGroupMembershipProvider(request_id_factory=request_id_factory, **kwargs)

    def test_group_one_maps_to_zero_based_xml_and_preserves_sparse_export_order(self):
        runtime = ExportRuntime(self.directory)
        result = self.provider().get_group_membership(runtime, 1, self.settings)
        self.assertEqual(result["fixtures"], [101, 1007, 2])
        self.assertEqual(result["members"], [
            {"fix_id": 101, "export_order": 0},
            {"fix_id": 1007, "export_order": 1},
            {"fix_id": 2, "export_order": 2},
        ])
        self.assertEqual(result["fixture_refs"], ["101", "1007", "2"])
        self.assertEqual(result["members_exact"], [
            {"fixture_ref": "101", "fix_id": 101, "export_order": 0},
            {"fixture_ref": "1007", "fix_id": 1007, "export_order": 1},
            {"fixture_ref": "2", "fix_id": 2, "export_order": 2},
        ])
        self.assertEqual(result["source"], "ma2_export_xml")
        self.assertEqual(runtime.commands, [(1, "ZEN_AGENT_G1_request0001.xml")])
        self.assertFalse((self.directory / "ZEN_AGENT_G1_request0001.xml").exists())


    def test_multi_instance_membership_preserves_exact_subfixture_identity(self):
        def exact_group_xml(*_args, **_kwargs):
            return '<MA><Group index="6" name="STROBE"><Subfixtures>'                 '<Subfixture fix_id="701" sub_index="2" />'                 '<Subfixture fix_id="702" sub_index="2" />'                 '</Subfixtures></Group></MA>'
        runtime = ExportRuntime(self.directory, xml_factory=exact_group_xml)
        result = self.provider().get_group_membership(runtime, 7, self.settings)
        self.assertEqual(result["fixtures"], [701, 702])
        self.assertEqual(result["fixture_refs"], ["701.2", "702.2"])
        self.assertEqual(result["members_exact"], [
            {"fixture_ref": "701.2", "fix_id": 701, "export_order": 0},
            {"fixture_ref": "702.2", "fix_id": 702, "export_order": 1},
        ])

    def test_32_member_export_sample_is_preserved(self):
        fixture_ids = [*range(101, 117), *range(129, 116, -1), 132, 130, 131]
        self.assertEqual(len(fixture_ids), 32)
        runtime = ExportRuntime(self.directory, xml_factory=lambda *_args, **_kwargs: group_xml(*fixture_ids))
        result = self.provider().get_group_membership(runtime, 1, self.settings)
        self.assertEqual(result["fixtures"], fixture_ids)
        self.assertEqual(result["members"][-1], {"fix_id": 131, "export_order": 31})

    def test_empty_real_group_is_not_an_error(self):
        runtime = ExportRuntime(self.directory, xml_factory=lambda *_args, **_kwargs: group_xml())
        self.assertEqual(self.provider().get_group_membership(runtime, 1, self.settings)["fixtures"], [])

    def test_wrong_group_or_malformed_xml_is_rejected_and_retained_for_diagnostics(self):
        wrong = ExportRuntime(self.directory, xml_factory=lambda *_args, **_kwargs: group_xml(101, index=1))
        with self.assertRaisesRegex(GroupMembershipProviderError, "GROUP_NUMBER_MISMATCH"):
            self.provider().get_group_membership(wrong, 1, self.settings)
        self.assertTrue((self.directory / "ZEN_AGENT_G1_request0001.xml").exists())
        (self.directory / "ZEN_AGENT_G1_request0001.xml").unlink()
        malformed = ExportRuntime(self.directory, xml_factory=lambda *_args, **_kwargs: "<MA><Group>")
        with self.assertRaisesRegex(GroupMembershipProviderError, "MALFORMED"):
            self.provider(poll_seconds=.01).get_group_membership(malformed, 1, {**self.settings, "timeout_seconds": .1})
        event, diagnostic = malformed.log_records[-1]
        self.assertEqual((event, diagnostic["error"], diagnostic["xml_well_formed"]), ("group_export_diagnostic", "EXPORT_XML_MALFORMED", False))
        self.assertTrue(Path(diagnostic["diagnostic_copy_path"]).is_file())

    def test_missing_subfixtures_is_rejected(self):
        runtime = ExportRuntime(self.directory, xml_factory=lambda *_args, **_kwargs: '<MA><Group index="0" name="HYBRID"><Selection /></Group></MA>')
        with self.assertRaisesRegex(GroupMembershipProviderError, "NO_MEMBERSHIP"):
            self.provider().get_group_membership(runtime, 1, self.settings)

    def test_fresh_unique_export_accepts_filesystem_mtime_skew(self):
        class SkewedRuntime(ExportRuntime):
            def export_group_file(inner, group_no, filename):
                inner.commands.append((group_no, filename))
                target = inner.directory / filename
                target.write_text(group_xml(101), encoding="utf-8")
                os.utime(target, ns=(1, 1))
                return "exported"

        provider = ExportFileGroupMembershipProvider(
            request_id_factory=lambda: "request0001",
            wall_clock_ns=lambda: 2_000_000_000,
            poll_seconds=.001,
        )
        result = provider.get_group_membership(
            SkewedRuntime(self.directory),
            1,
            {**self.settings, "timeout_seconds": 0.5},
        )
        self.assertEqual(result["fixtures"], [101])

    def test_cleanup_is_limited_to_agent_owned_prefix(self):
        unrelated = self.directory / "keep-this.xml"
        unrelated.write_text("unrelated", encoding="utf-8")
        self.provider().get_group_membership(ExportRuntime(self.directory), 1, self.settings)
        self.assertTrue(unrelated.exists())

    def test_remote_host_reports_explicit_filesystem_capability_error(self):
        runtime = ExportRuntime(self.directory, host="10.20.30.40")
        provider = self.provider()
        self.assertFalse(provider.capabilities(runtime, self.settings)["local_export_access"])
        with self.assertRaisesRegex(GroupMembershipProviderUnavailable, "REMOTE_EXPORT_ACCESS_UNAVAILABLE"):
            provider.get_group_membership(runtime, 1, self.settings)
        self.assertEqual(runtime.commands, [])

    def test_unique_filenames_keep_concurrent_exports_independent(self):
        request_ids = iter(("request0001", "request0002"))
        provider = self.provider(lambda: next(request_ids))
        runtime = ExportRuntime(self.directory)
        results, errors = [], []

        def run():
            try:
                results.append(provider.get_group_membership(runtime, 1, self.settings))
            except Exception as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        threads = [threading.Thread(target=run), threading.Thread(target=run)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual({filename for _group, filename in runtime.commands}, {"ZEN_AGENT_G1_request0001.xml", "ZEN_AGENT_G1_request0002.xml"})

    def test_partial_write_waits_for_stable_well_formed_xml(self):
        class StepClock:
            value = 0.0
            def __call__(self):
                current = self.value
                self.value += .05
                return current

        class PartialRuntime(ExportRuntime):
            def export_group_file(inner, group_no, filename):
                inner.commands.append((group_no, filename))
                inner.target = inner.directory / filename
                inner.target.write_text('<MA><Group index="0" name="HYBRID">', encoding="utf-8")
                return "exported"

            def finish(inner, _seconds):
                if "</MA>" not in inner.target.read_text(encoding="utf-8"):
                    inner.target.write_text(group_xml(101, 102), encoding="utf-8")

        runtime = PartialRuntime(self.directory)
        provider = ExportFileGroupMembershipProvider(request_id_factory=lambda: "request0001", wall_clock_ns=lambda: 0, monotonic_clock=StepClock(), sleep=runtime.finish)
        self.assertEqual(provider.get_group_membership(runtime, 1, self.settings)["fixtures"], [101, 102])

    def test_owned_stale_file_is_replaced_before_export(self):
        target = self.directory / "ZEN_AGENT_G1_request0001.xml"
        target.write_text(group_xml(999), encoding="utf-8")

        class CheckingRuntime(ExportRuntime):
            def export_group_file(inner, group_no, filename):
                inner.assert_no_stale = not (inner.directory / filename).exists()
                return super().export_group_file(group_no, filename)

        runtime = CheckingRuntime(self.directory)
        self.assertEqual(self.provider().get_group_membership(runtime, 1, self.settings)["fixtures"], [101, 1007, 2])
        self.assertTrue(runtime.assert_no_stale)

    def test_group_and_layout_exports_are_serialized_as_one_transaction(self):
        class CoordinatedRuntime(ExportRuntime):
            def __init__(inner, directory):
                super().__init__(directory)
                inner.lock = threading.RLock()
                inner.active = inner.max_active = 0

            @contextmanager
            def export_transaction(inner):
                with inner.lock:
                    inner.active += 1
                    inner.max_active = max(inner.max_active, inner.active)
                    try:
                        yield
                    finally:
                        inner.active -= 1

            def export_group_file(inner, group_no, filename):
                time.sleep(.02)
                return super().export_group_file(group_no, filename)

            def export_layout_file(inner, layout_no, filename):
                time.sleep(.02)
                (inner.directory / filename).write_text(f'<MA><Group index="{layout_no - 1}" name="Test"><LayoutData><CObjects /></LayoutData></Group></MA>', encoding="utf-8")
                return "exported"

        runtime = CoordinatedRuntime(self.directory)
        provider = self.provider()
        layout = LayoutExportProvider()
        failures: list[Exception] = []
        threads = [
            threading.Thread(target=lambda: self._capture(failures, lambda: provider.get_group_membership(runtime, 1, self.settings))),
            threading.Thread(target=lambda: self._capture(failures, lambda: layout.get_layout(runtime, 1, self.settings))),
        ]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(failures, [])
        self.assertEqual(runtime.max_active, 1)

    @staticmethod
    def _capture(errors, operation):
        try:
            operation()
        except Exception as exc:  # pragma: no cover - asserted by caller
            errors.append(exc)

    def test_auto_resolver_prefers_the_running_onpc_version_then_newest(self):
        program_data = self.directory / "ProgramData"
        base = program_data / "MA Lighting Technologies" / "grandma"
        (base / "gma2_V_3.9.60" / "importexport").mkdir(parents=True)
        (base / "gma2_V_3.9.61" / "importexport").mkdir(parents=True)
        resolver = ImportExportPathResolver(program_data, running_onpc_paths=lambda: [Path(r"C:\\Program Files\\MA Lighting Technologies\\grandma\\grandMA2 onPC 3.9.60.65\\gma2onpc.exe")])
        self.assertEqual(resolver.resolve(), (base / "gma2_V_3.9.60" / "importexport").resolve())
        latest = ImportExportPathResolver(program_data, running_onpc_paths=lambda: [])
        self.assertEqual(latest.resolve(), (base / "gma2_V_3.9.61" / "importexport").resolve())


if __name__ == "__main__":
    unittest.main()
