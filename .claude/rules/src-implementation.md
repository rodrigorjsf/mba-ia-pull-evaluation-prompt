---
paths:
  - "src/**/*.py"
---

# Implementing code in `src/`

- `evaluate.py`, `metrics.py`, and `utils.py` are immutable challenge files — never edit them; the TDD mandate below applies only to the deliverables you implement (`pull_prompts.py`, `push_prompts.py`).
- Drive every change to those deliverables through the `/tdd` skill (red-green-refactor): write a failing test first, make it pass, then refactor — no implementation code without a failing test first (see root `CLAUDE.md`).
- Reuse the helpers in the immutable `utils.py` (`load_yaml`, `save_yaml`, `check_env_vars`, `validate_prompt_structure`, `get_llm`) instead of reimplementing YAML I/O, env checks, or prompt validation.
