# xhx-skills

A collection of agent skills. Each skill lives in its own folder under `skills/`.

## Skills

| Skill | What it does |
| --- | --- |
| [final-polish](skills/final-polish) | Appends a concise, human-style note to an agent's final answer — approach, what changed, and why. |

## Install

Install one skill:

```bash
npx skills add xiao-huixing/xhx-skills@final-polish
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
