import json
import re
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
REPOSITORY = SKILL.parents[1]


class SkillContractTest(unittest.TestCase):
    def test_router_is_lean_and_has_mode_fast_paths(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(content.splitlines()), 100)
        self.assertIn("workflow.py status", content)
        self.assertIn("workflow.py history", content)
        self.assertNotIn("## Shared startup protocol", content)

    def test_description_has_trigger_boundaries(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        description = re.search(r"description: >-\n(?P<body>(?:  .*\n)+)", content)
        self.assertIsNotNone(description)
        body = description.group("body")
        self.assertIn("Do not use", body)
        self.assertNotIn("Use whenever", body)
        self.assertIn("durable", body.casefold())

    def test_simple_work_does_not_initialize_tracking(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Admission gate", content)
        self.assertIn("Do not initialize `.ai-workflow`", content)

    def test_protocol_uses_canonical_waiting_state(self):
        paths = [SKILL / "SKILL.md", *(SKILL / "references").glob("*.md")]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("waiting_plan_approval", combined)
        self.assertIn("state: waiting_input", combined)
        self.assertIn("work-item.yaml", combined)
        self.assertIn("events.jsonl", combined)
        self.assertNotIn("manifest.yaml", combined)
        self.assertNotIn("tasks.yaml", combined)
        self.assertNotIn("execution/state.yaml", combined)
        self.assertNotIn(".sqlite", combined)

    def test_plugin_does_not_force_generic_invocation(self):
        manifest = json.loads((REPOSITORY / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        default_prompt = manifest["interface"].get("defaultPrompt", "")
        self.assertNotIn("Use ai-workflow for plan, execute, review", default_prompt)

    def test_evals_use_skill_creator_schema_and_fixture_inputs(self):
        evals = json.loads((SKILL / "evals/evals.json").read_text(encoding="utf-8"))
        for case in evals["evals"]:
            self.assertIn("expectations", case)
            self.assertTrue(case["files"])
            self.assertTrue(all((SKILL / path).exists() for path in case["files"]))


if __name__ == "__main__":
    unittest.main()
