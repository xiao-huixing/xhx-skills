# xhx-skills

A collection of agent skills. Each skill lives in its own folder under `skills/`.

## Skills

| Skill | What it does |
| --- | --- |
| [final-response](skills/final-response) | Completion check before an agent sends its final answer — appends a short note on what changed, the path taken, and why. |
| [explain-code-flow](skills/explain-code-flow) | Reads backend code and explains end-to-end business flows, all interfaces, and each interface's execution process without detailed code. |

## Install

Install one skill:

```bash
npx skills add xiao-huixing/xhx-skills@final-response
```

Replace `final-response` with `explain-code-flow` to install the backend flow analysis skill.

Install interactively (the CLI lists every skill in this repo):

```bash
npx skills add xiao-huixing/xhx-skills
```

Works with Claude Code, Cursor, Codex, Windsurf, and other agents supported by
the [skills CLI](https://github.com/vercel-labs/skills). Repository-level plugin
registration is available in `.claude-plugin/plugin.json` and
`.codex-plugin/plugin.json`.

## Add a new skill

1. Create `skills/<skill-name>/SKILL.md`.
2. Frontmatter requires `name` (kebab-case) and `description`.
3. Add a row to the table above.

That's it — the skills CLI discovers every `skills/*/SKILL.md` automatically.

## License

MIT
