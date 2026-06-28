---
paths:
  - "prompts/bug_to_user_story_v2.yml"
---

# Authoring the v2 prompt artifact

This file is the graded deliverable, but it is scored only after it is pushed to the Hub — `evaluate.py` pulls the published `<handle>/bug_to_user_story_v2`, never this local YAML, so editing it alone changes no metric until you re-push. All five metrics must reach >= 0.8.

- Keep the YAML flat with top-level keys; never nest under a root like `bug_to_user_story_v2:` (v1.yml nests under `bug_to_user_story_v1:` — do not copy that shape), because `validate_prompt_structure` reads top-level `description`, `system_prompt`, `version`, and `techniques_applied`.
- Set `user_prompt` to exactly `"{bug_report}"`; `{bug_report}` is the only template variable.
- Escape every literal brace in the `system_prompt` text as `{{` and `}}`, so few-shot text is not parsed as a template variable.
- Keep persona, behavioral rules, few-shot examples, and the output-format demand inside `system_prompt`.
- Define an explicit persona (e.g. "Você é um Product Manager...") so Role Prompting applies and `test_prompt_has_role_definition` passes.
- Demand a Markdown User Story output: `Como um... eu quero... para que...` plus `Critérios de Aceitação` as `Dado/Quando/Então`.
- Instruct the model to reason internally and emit only the final User Story — no preamble, code fences, or visible chain-of-thought, because visible text lowers Precision and F1.
- Provide 2–3 few-shot examples whose bugs differ from the 15 items in `datasets/bug_to_user_story.jsonl`, so the format is taught without memorizing the graded set.
- Handle edge cases explicitly: a vague bug, several bugs in one report, and missing detail.
- List at least two techniques in `techniques_applied` (e.g. Few-shot Learning, Role Prompting, Chain of Thought); fewer than two fails `validate_prompt_structure` and `test_minimum_techniques`.
- Leave no `TODO` text anywhere; `validate_prompt_structure` rejects `TODO` in `system_prompt` and `test_prompt_no_todos` checks the artifact.
- Optimize Precision hardest by keeping the output factually faithful to the `reference`, since Precision feeds both Helpfulness and Correctness.
