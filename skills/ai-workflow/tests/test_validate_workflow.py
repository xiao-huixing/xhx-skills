import json
import tempfile
import unittest
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from validate_workflow import validate_root  # noqa: E402


class ValidateWorkflowTest(unittest.TestCase):
    def write_minimal_workflow(self, root: Path) -> Path:
        workflow = root / ".ai-workflow"
        for relative in (
            "project/overview.md",
            "project/modules.yaml",
            "capabilities/index.yaml",
            "indexes/active.yaml",
            "work-items/2026/REQ-20260807-001-demo/manifest.yaml",
            "work-items/2026/REQ-20260807-001-demo/context.md",
            "work-items/2026/REQ-20260807-001-demo/tasks.yaml",
            "work-items/2026/REQ-20260807-001-demo/execution/state.yaml",
        ):
            target = workflow / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{}\n", encoding="utf-8")
        events = workflow / "work-items/2026/REQ-20260807-001-demo/execution/events.ndjson"
        events.write_text(
            json.dumps(
                {
                    "id": "EVT-0001",
                    "at": "2026-08-07T00:00:00Z",
                    "actor": "test",
                    "type": "work_item.created",
                    "refs": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return workflow

    def test_valid_minimal_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow = self.write_minimal_workflow(Path(directory))
            self.assertEqual([], validate_root(workflow))

    def test_invalid_event_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow = self.write_minimal_workflow(Path(directory))
            events = workflow / "work-items/2026/REQ-20260807-001-demo/execution/events.ndjson"
            events.write_text("not-json\n", encoding="utf-8")
            errors = validate_root(workflow)
            self.assertTrue(any("invalid JSON" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
