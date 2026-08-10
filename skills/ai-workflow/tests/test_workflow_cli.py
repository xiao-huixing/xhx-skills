import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workflow.py"


class WorkflowCliTest(unittest.TestCase):
    def run_cli(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(expected, result.returncode, result.stderr or result.stdout)
        return result

    def init_workflow(self, directory: str) -> tuple[Path, str]:
        root = Path(directory) / ".ai-workflow"
        result = self.run_cli(
            "init",
            "--root",
            str(root),
            "--title",
            "Demo requirement",
            "--date",
            "20260810",
            "--track",
            "light",
        )
        payload = json.loads(result.stdout)
        return root, payload["work_item"]

    def write_tasks(self, root: Path, work_item: str, tasks: list[dict]) -> Path:
        path = root / "work-items/2026" / work_item / "tasks.yaml"
        path.write_text(json.dumps(tasks), encoding="utf-8")
        return path

    def task(self, task_id: str, depends_on: list[str] | None = None) -> dict:
        return {
            "id": task_id,
            "revision": "R001",
            "title": task_id,
            "status": "pending",
            "depends_on": depends_on or [],
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

    def plan_ready(self, root: Path, work_item: str) -> None:
        self.run_cli("plan-ready", "--root", str(root), "--work-item", work_item)

    def test_status_missing_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".ai-workflow"
            result = self.run_cli("status", "--root", str(root), "--format", "json")
            self.assertEqual("not_initialized", json.loads(result.stdout)["status"])
            self.assertFalse(root.exists())

    def test_init_validate_resolve_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root, work_item = self.init_workflow(directory)
            self.assertEqual("REQ-20260810-001-demo-requirement", work_item)
            self.run_cli("validate", "--root", str(root), "--work-item", work_item)
            resolved = self.run_cli("resolve", "--root", str(root), work_item)
            self.assertEqual(work_item, json.loads(resolved.stdout)["work_item"])
            status = self.run_cli(
                "status", "--root", str(root), "--work-item", work_item, "--format", "json"
            )
            payload = json.loads(status.stdout)
            self.assertEqual("plan", payload["phase"])
            self.assertEqual("light", payload["track"])
            self.assertEqual({"total": 0, "passed": 0, "blocked": 0}, payload["tasks"])

    def test_init_accepts_ascii_slug_for_non_latin_title(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".ai-workflow"
            result = self.run_cli(
                "init",
                "--root",
                str(root),
                "--title",
                "会员折扣",
                "--slug",
                "member-discount",
                "--date",
                "20260810",
            )
            self.assertEqual(
                "REQ-20260810-001-member-discount",
                json.loads(result.stdout)["work_item"],
            )

    def test_invalid_init_slug_does_not_create_workflow_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".ai-workflow"
            result = self.run_cli(
                "init",
                "--root",
                str(root),
                "--title",
                "会员折扣",
                "--slug",
                "Member Discount",
                "--date",
                "20260810",
                expected=2,
            )
            self.assertIn("slug", result.stderr)
            self.assertFalse(root.exists())

    def test_task_transition_is_idempotent_and_finishes_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root, work_item = self.init_workflow(directory)
            self.write_tasks(root, work_item, [self.task("TASK-001")])
            blocked = self.run_cli(
                "approve-plan",
                "--root",
                str(root),
                "--work-item",
                work_item,
                expected=1,
            )
            self.assertIn("plan-ready", blocked.stderr)
            self.plan_ready(root, work_item)
            self.run_cli("approve-plan", "--root", str(root), "--work-item", work_item)
            self.run_cli(
                "task",
                "begin",
                "--root",
                str(root),
                "--work-item",
                work_item,
                "--task",
                "TASK-001",
                "--idempotency-key",
                "begin-task-1",
            )
            self.run_cli(
                "task",
                "begin",
                "--root",
                str(root),
                "--work-item",
                work_item,
                "--task",
                "TASK-001",
                "--idempotency-key",
                "begin-task-1",
            )
            item = root / "work-items/2026" / work_item
            events = (item / "execution/events.ndjson").read_text(encoding="utf-8").splitlines()
            self.assertEqual(4, len(events))
            failed = self.run_cli(
                "task",
                "pass",
                "--root",
                str(root),
                "--work-item",
                work_item,
                "--task",
                "TASK-001",
                expected=2,
            )
            self.assertIn("evidence", failed.stderr)
            self.run_cli(
                "task",
                "pass",
                "--root",
                str(root),
                "--work-item",
                work_item,
                "--task",
                "TASK-001",
                "--evidence",
                "tests passed",
                "--idempotency-key",
                "pass-task-1",
            )
            status = self.run_cli(
                "status", "--root", str(root), "--work-item", work_item, "--format", "json"
            )
            payload = json.loads(status.stdout)
            self.assertEqual("review", payload["phase"])
            self.assertEqual("implemented", payload["delivery"])
            self.assertEqual(1, payload["tasks"]["passed"])
            self.run_cli("validate", "--root", str(root), "--work-item", work_item)
            review_args = (
                "review",
                "--root",
                str(root),
                "--work-item",
                work_item,
                "--result",
                "passed",
                "--idempotency-key",
                "review-task-1",
            )
            self.run_cli(*review_args)
            repeated_review = self.run_cli(*review_args)
            self.assertEqual("idempotent", json.loads(repeated_review.stdout)["status"])
            completed = self.run_cli(
                "status", "--root", str(root), "--work-item", work_item, "--format", "json"
            )
            completed_payload = json.loads(completed.stdout)
            self.assertEqual("done", completed_payload["phase"])
            self.assertEqual("completed", completed_payload["state"])
            active = self.run_cli("status", "--root", str(root), "--format", "json")
            self.assertEqual([], json.loads(active.stdout)["active"])
            self.run_cli("validate", "--root", str(root), "--work-item", work_item)

    def test_dependency_and_illegal_transition_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, work_item = self.init_workflow(directory)
            self.write_tasks(
                root,
                work_item,
                [self.task("TASK-001"), self.task("TASK-002", ["TASK-001"])],
            )
            self.plan_ready(root, work_item)
            self.run_cli("approve-plan", "--root", str(root), "--work-item", work_item)
            blocked = self.run_cli(
                "task",
                "begin",
                "--root",
                str(root),
                "--work-item",
                work_item,
                "--task",
                "TASK-002",
                expected=1,
            )
            self.assertIn("dependency", blocked.stderr)
            illegal = self.run_cli(
                "task",
                "pass",
                "--root",
                str(root),
                "--work-item",
                work_item,
                "--task",
                "TASK-001",
                "--evidence",
                "tests passed",
                expected=1,
            )
            self.assertIn("in_progress", illegal.stderr)

    def test_mutation_recovers_interrupted_transaction_before_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root, work_item = self.init_workflow(directory)
            self.write_tasks(root, work_item, [self.task("TASK-001")])
            transaction = root / ".transactions/interrupted"
            transaction.mkdir(parents=True)
            target = f"work-items/2026/{work_item}/context.md"
            (transaction / "0000.tmp").write_text("# Recovered Context\n", encoding="utf-8")
            (transaction / "transaction.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "files": [{"target": target, "staged": "0000.tmp"}],
                    }
                ),
                encoding="utf-8",
            )

            self.plan_ready(root, work_item)
            self.run_cli("approve-plan", "--root", str(root), "--work-item", work_item)

            context = root / target
            self.assertIn("Current Context", context.read_text(encoding="utf-8"))
            self.assertFalse((root / ".transactions").exists())

    def test_transaction_recovery_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root, work_item = self.init_workflow(directory)
            self.write_tasks(root, work_item, [self.task("TASK-001")])
            transaction = root / ".transactions/untrusted"
            transaction.mkdir(parents=True)
            (transaction / "0000.tmp").write_text("escape", encoding="utf-8")
            (transaction / "transaction.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "files": [{"target": "../escape.txt", "staged": "0000.tmp"}],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli(
                "plan-ready",
                "--root",
                str(root),
                "--work-item",
                work_item,
                expected=1,
            )

            self.assertIn("outside workflow root", result.stderr)
            self.assertFalse((Path(directory) / "escape.txt").exists())

    def test_mutation_discards_transaction_without_commit_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root, work_item = self.init_workflow(directory)
            self.write_tasks(root, work_item, [self.task("TASK-001")])
            transaction = root / ".transactions/not-committed"
            transaction.mkdir(parents=True)
            (transaction / "0000.tmp").write_text("staged only", encoding="utf-8")

            self.plan_ready(root, work_item)

            self.assertFalse((root / ".transactions").exists())

    def test_history_missing_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".ai-workflow"
            result = self.run_cli("history", "--root", str(root), "demo")
            self.assertEqual([], json.loads(result.stdout)["matches"])
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
