## Agent skills

### Issue tracker

Issues live in GitHub Issues for this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — one `CONTEXT.md` + `docs/adr/` at repo root. See `docs/agents/domain.md`.

## Implementation — TDD is mandatory

**Every code change in this repo, without exception, is driven through the `/tdd`
skill** (red-green-refactor): write a failing test first, make it pass, then
refactor. Non-negotiable — applies to all of `src/` and any other code here. Never
write or edit implementation code without a failing test first.

## Documentation

Postgraduate deliverable: docs are living, not write-once.

- `README.md` and `docs/ROADMAP.md` must stay in sync with the code. Update them in the **same commit** that changes behavior, scope, or run steps — never let them drift.
- Use **Mermaid diagrams** whenever they make a flow, architecture, or state clearer. Apply colors (`classDef`/`style`) and animated edges (`e1@{ animate: true }`) where the renderer supports them; colors are the baseline, animation is best-effort.

## Applied Learning

When something fails repeatedly, when User has to re-explain, or when a workaround is found for a platform/tool limitation, add a one-line bullet here. Keep each bullet under 15 words. No explanations. Only add things that will save time in future sessions.

- Agents fail silently on wrong paths. Always verify hardcoded paths.
- Deps need Python 3.12 (no 3.14 wheels); use `uv venv --python 3.12`.
- Orchestrate `commands.json` needs a no-op `build` (`/usr/bin/true`) or reverify fails.
- MCP git commits need repo-local `git config user.name/email` (no HOME).
- Eval must run sequentially (conc=1); gpt-4o judge 30k TPM, else 429 zeros metrics.
- Prompt validator flags "TODO" inside "TODOS"; use lowercase "todos" in system_prompt.
- Local probe reads YAML directly (skips validation); only push validates structure.
- chrome-devtools MCP tools register only at CC startup; Bash-launched Chrome dies (exit 144).
