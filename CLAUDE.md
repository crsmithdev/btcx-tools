# btcx-tools

Read [PRINCIPLES.md](PRINCIPLES.md) before a design, review or code change. Its rules win over habit.

## Development

- Each change is made on a branch in a worktree at `.worktrees/<name>`. It lands on `main` as a squash merge.
- Run `uv run btcx fetch` in the worktree before you run a command. `data/` and `out/` are relative to the current directory.
- A change to a decoder is verified by the command that uses it, run on the pinned files, with its output compared to the numbers in the README.
