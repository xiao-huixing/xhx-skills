import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from validate_workflow import validate_root  # noqa: E402


class ValidateWorkflowTest(unittest.TestCase):
    def write_valid_workflow(self, root: Path) -> tuple[Path, Path]:
        workflow = root / ".ai-workflow"
        item = workflow / "work-items/2026/REQ-20260810-001-demo"
        files = {
            workflow / "project/overview.md": "# Project Overview\n",
            workflow / "project/modules.yaml": "[]\n",
            workflow / "capabilities/index.yaml": "[]\n",
            workflow / "indexes/active.yaml": "[]\n",
            workflow / "indexes/catalog.jsonl": "",
            item / "manifest.yaml": json.dumps(
                {
                    "schema_version": 1,
                    "id": "REQ-20260810-001-demo",
                    "kind": "requirement",
                    "title": "Demo",
                    "aliases": [],
                    "track": "light",
                    "phase": "plan",
                    "state": "waiting_input",
                    "delivery": "not_started",
                    "current_revision": "R001",
                    "base_commit": None,
                    "capabilities": [],
                    "modules": [],
                    "parent": None,
                    "supersedes": [],
                    "gates": {
                        "plan_approved": False,
                        "review_approved": False,
                        "release_approved": False,
                    },
                    "active_task": None,
                    "next_action": "write_plan",
                    "last_event": "EVT-000001",
                    "updated_at": "2026-08-10T00:00:00+00:00",
                }
            ),
            item / "context.md": "# Current Context\n",
            item / "tasks.yaml": "[]\n",
            item / "execution/state.yaml": json.dumps(
                {
                    "schema_version": 1,
                    "phase": "plan",
                    "state": "waiting_input",
                    "active_task": None,
                    "last_success": None,
                    "blocked_by": [],
                    "next_action": "write_plan",
                    "updated_at": "2026-08-10T00:00:00+00:00",
                }
            ),
            item / "execution/events.ndjson": json.dumps(
                {
                    "id": "EVT-000001",
                    "at": "2026-08-10T00:00:00+00:00",
                    "actor": "test",
                    "type": "work_item.created",
                    "refs": [],
                }
            )
            + "\n",
        }
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return workflow, item

    def test_valid_workflow_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, _ = self.write_valid_workflow(Path(directory))
            self.assertEqual([], validate_root(workflow))

    def test_empty_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            (item / "manifest.yaml").write_text("{}\n", encoding="utf-8")
            errors = validate_root(workflow)
            self.assertTrue(any("manifest missing" in error for error in errors))

    def test_manifest_requires_complete_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            manifest_path = item / "manifest.yaml"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_path.write_text(
                json.dumps({key: value for key, value in manifest.items() if key != "aliases"}),
                encoding="utf-8",
            )
            errors = validate_root(workflow)
            self.assertIn("manifest missing aliases", errors)

    def test_invalid_state_and_state_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            state_path = item / "execution/state.yaml"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state_path.write_text(
                json.dumps({**state, "state": "waiting_plan_approval"}),
                encoding="utf-8",
            )
            errors = validate_root(workflow)
            self.assertTrue(any("invalid state" in error for error in errors))
            self.assertTrue(any("state drift" in error for error in errors))

    def test_invalid_event_and_task_dependency_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            (item / "execution/events.ndjson").write_text("not-json\n", encoding="utf-8")
            (item / "tasks.yaml").write_text(
                json.dumps(
                    [
                        {
                            "id": "TASK-001",
                            "revision": "R001",
                            "title": "Demo task",
                            "status": "pending",
                            "depends_on": ["TASK-404"],
                            "requirements": ["REQ-DEMO-001"],
                            "acceptance": ["AC-001"],
                            "scope": ["src/demo.py"],
                            "expected_behavior": "Demo works",
                            "validation": ["python -m unittest"],
                            "evidence": [],
                            "rollback": "Revert the change",
                            "done_condition": "Tests pass",
                            "attempt": 0,
                            "failure": None,
                            "last_event": None,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            errors = validate_root(workflow)
            self.assertTrue(any("invalid JSON" in error for error in errors))
            self.assertTrue(any("unknown dependency" in error for error in errors))

    def test_empty_event_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            event_path = item / "execution/events.ndjson"
            event = json.loads(event_path.read_text(encoding="utf-8"))
            event_path.write_text(json.dumps({**event, "type": ""}) + "\n", encoding="utf-8")
            errors = validate_root(workflow)
            self.assertIn("event type must be a non-empty string: EVT-000001", errors)


if __name__ == "__main__":
    unittest.main()
