import json
import re
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]


class SkillContractTest(unittest.TestCase):
    def test_description_does_not_force_every_bug_into_tracking(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        description = re.search(r"description: >-\n(?P<body>(?:  .*\n)+)", content)
        self.assertIsNotNone(description)
        body = description.group("body")
        self.assertNotIn("whenever", body.casefold())
        self.assertIn("Do not use", body)

    def test_simple_bug_uses_non_persistent_fast_lane(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Fast lane", content)
        self.assertIn("Do not create `.ai-workflow`", content)
        self.assertIn("default", content.casefold())

    def test_tracked_protocol_uses_two_file_storage(self):
        protocol = (SKILL / "references/bug-protocol.md").read_text(encoding="utf-8")
        self.assertIn("work-item.yaml", protocol)
        self.assertIn("events.jsonl", protocol)
        for legacy_path in ("manifest.yaml", "tasks.yaml", "context.md", "events.ndjson"):
            self.assertNotIn(legacy_path, protocol)

    def test_evals_cover_simple_bug_without_workflow_files(self):
        evals = json.loads((SKILL / "evals/evals.json").read_text(encoding="utf-8"))
        expectations = [
            expectation
            for case in evals["evals"]
            for expectation in case.get("expectations", [])
        ]
        self.assertTrue(any("不创建 .ai-workflow" in expectation for expectation in expectations))


if __name__ == "__main__":
    unittest.main()
