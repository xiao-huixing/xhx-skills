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
            item / "work-item.yaml": json.dumps(
                {
                    "schema_version": 2,
                    "id": "REQ-20260810-001-demo",
                    "kind": "requirement",
                    "title": "Demo",
                    "aliases": [],
                    "track": "light",
                    "phase": "plan",
                    "state": "waiting_input",
                    "delivery": "not_started",
                    "current_revision": "R001",
                    "revisions": [
                        {
                            "id": "R001",
                            "input": "Demo",
                            "plan": None,
                            "delta": None,
                            "status": "draft",
                            "approved_at": None,
                        }
                    ],
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
                    "tasks": [],
                    "decisions": [],
                    "review": {"result": None, "at": None, "findings": []},
                    "summary": "Demo",
                    "evidence": [],
                }
            ),
            item / "events.jsonl": json.dumps(
                {
                    "schema_version": 1,
                    "id": "EVT-000001",
                    "work_item_id": "REQ-20260810-001-demo",
                    "sequence": 1,
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

    def test_empty_work_item_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            (item / "work-item.yaml").write_text("{}\n", encoding="utf-8")
            errors = validate_root(workflow)
            self.assertTrue(any("work-item missing" in error for error in errors))

    def test_work_item_requires_complete_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            record_path = item / "work-item.yaml"
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record_path.write_text(
                json.dumps({key: value for key, value in record.items() if key != "aliases"}),
                encoding="utf-8",
            )
            errors = validate_root(workflow)
            self.assertIn("work-item missing aliases", errors)

    def test_invalid_state_and_event_pointer_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            record_path = item / "work-item.yaml"
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record_path.write_text(
                json.dumps({**record, "state": "waiting_plan_approval", "last_event": "EVT-404"}),
                encoding="utf-8",
            )
            errors = validate_root(workflow)
            self.assertTrue(any("invalid state" in error for error in errors))
            self.assertTrue(any("unknown work-item last_event" in error for error in errors))

    def test_invalid_event_and_task_dependency_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            (item / "events.jsonl").write_text("not-json\n", encoding="utf-8")
            record_path = item / "work-item.yaml"
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record_path.write_text(
                json.dumps(
                    {
                        **record,
                        "tasks": [{
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
                        }],
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_root(workflow)
            self.assertTrue(any("invalid JSON" in error for error in errors))
            self.assertTrue(any("unknown dependency" in error for error in errors))

    def test_empty_event_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            event_path = item / "events.jsonl"
            event = json.loads(event_path.read_text(encoding="utf-8"))
            event_path.write_text(json.dumps({**event, "type": ""}) + "\n", encoding="utf-8")
            errors = validate_root(workflow)
            self.assertIn("event type must be a non-empty string: EVT-000001", errors)

    def test_event_sequence_and_exact_two_file_layout_are_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            event_path = item / "events.jsonl"
            event = json.loads(event_path.read_text(encoding="utf-8"))
            event_path.write_text(json.dumps({**event, "sequence": 2}) + "\n", encoding="utf-8")
            (item / "manifest.yaml").write_text("{}\n", encoding="utf-8")

            errors = validate_root(workflow)

            self.assertTrue(any("event sequence" in error for error in errors))
            self.assertTrue(any("unexpected work-item file: manifest.yaml" in error for error in errors))

    def test_legacy_layout_is_rejected_without_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow, item = self.write_valid_workflow(Path(directory))
            record_path = item / "work-item.yaml"
            legacy_path = item / "manifest.yaml"
            legacy_path.write_text(record_path.read_text(encoding="utf-8"), encoding="utf-8")
            record_path.unlink()

            errors = validate_root(workflow)

            self.assertTrue(any("legacy storage layout is unsupported" in error for error in errors))
            self.assertTrue(legacy_path.exists())


if __name__ == "__main__":
    unittest.main()
