# Installed Skills

This project installs two Matt Pocock skills from GitHub:

- `grill-me`
- `to-issues`

Source repository:

```text
https://github.com/mattpocock/skills
```

Installed by:

```bash
npx skills@latest add mattpocock/skills --skill grill-me to-issues --agent opencode --copy --yes
```

Local files:

```text
.agents/skills/grill-me/SKILL.md
.agents/skills/to-issues/SKILL.md
skills-lock.json
```

## Usage In This Practice Project

- `grill-me`: used as a method for stress-testing specs and design decisions before implementation.
- `to-issues`: used as a method for turning PRDs into issue-style task files with `depends_on`, `acceptance`, and schema expectations.

These skills document workflow methods. They do not create hard security boundaries by themselves.
