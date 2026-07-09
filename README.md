# xhx-skills

A collection of agent skills. Each skill lives in its own folder under `skills/`.

## Skills

| Skill | What it does |
| --- | --- |
| [final-response](skills/final-response) | Completion check before an agent sends its final answer — appends a short note on what changed, the path taken, and why. |

## Install

Install one skill:

```bash
npx skills add xiao-huixing/xhx-skills@final-response
```

Install interactively (the CLI lists every skill in this repo):

```bash
npx skills add xiao-huixing/xhx-skills
```

Works with Claude Code, Cursor, Codex, Windsurf, and other agents supported by
the [skills CLI](https://github.com/vercel-labs/skills).

## Add a new skill

1. Create `skills/<skill-name>/SKILL.md`.
2. Frontmatter requires `name` (kebab-case) and `description`.
3. Add a row to the table above.

That's it — the skills CLI discovers every `skills/*/SKILL.md` automatically.

## License

MIT
