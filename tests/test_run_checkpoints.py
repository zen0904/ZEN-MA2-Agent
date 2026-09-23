import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zen_ma2_agent.run_checkpoints import (
    find_resume_point,
    read_step_artifact,
    write_step_artifact,
)


class RunCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.zen_home = Path(self.temporary_directory.name)
        self.environment = patch.dict(os.environ, {"ZEN_HOME": str(self.zen_home)})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_write_then_read_preserves_artifact(self):
        artifact = {"result": "complete", "details": ["one", "two"]}

        path = write_step_artifact("run-001", "designer", artifact)

        self.assertEqual(
            path,
            self.zen_home.resolve() / "projects" / "runs" / "run-001" / "steps" / "designer.json",
        )
        self.assertEqual(read_step_artifact("run-001", "designer"), artifact)

    def test_read_missing_artifact_returns_none(self):
        self.assertIsNone(read_step_artifact("run-001", "researcher"))

    def test_find_resume_point_for_partial_complete_and_unstarted_runs(self):
        roles = ["researcher", "designer", "critic"]
        write_step_artifact("partial", "researcher", {})
        write_step_artifact("complete", "researcher", {})
        write_step_artifact("complete", "designer", {})
        write_step_artifact("complete", "critic", {})

        self.assertEqual(find_resume_point("partial", roles), "designer")
        self.assertIsNone(find_resume_point("complete", roles))
        self.assertEqual(find_resume_point("unstarted", roles), "researcher")


if __name__ == "__main__":
    unittest.main()
