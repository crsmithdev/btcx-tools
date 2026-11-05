# btcx-tools

Read [PRINCIPLES.md](PRINCIPLES.md) before a design, review or code change. Its rules win over habit.

## Development

- Each change is made on a branch in a worktree at `.worktrees/<name>`. It lands on `main` as a squash merge.
- Run `uv run btcx fetch` in the worktree before you run a command. `data/` and `out/` are in the project directory.
- Verify a change with `uv run pytest`: it runs every finding in `btcx/findings.py` and the user-error cases. CI also runs `ruff check` and `ruff format --check`.
- Use the names in [GLOSSARY.md](GLOSSARY.md).
