# Prompt Optimization Challenge

The ubiquitous language for an MBA deliverable that pulls a low-quality prompt
from the LangSmith Prompt Hub, refactors it, pushes it back, and proves all five
evaluation metrics reach ≥ 0.8. Glossary only — no implementation details.

## Domain

**Bug Report**:
The raw, unstructured description of a defect that is the *input* to the prompt.
The dataset key is `bug_report`; it is the only template variable the prompt may require.

**User Story**:
The structured *output* the prompt must produce, in the form
`Como um <persona>, eu quero <ação>, para que <benefício>` followed by an
`Acceptance Criteria` block. The whole optimization goal is to make the model
reproduce this shape.

**Acceptance Criteria**:
The testable conditions appended to a User Story, written in Given-When-Then form
(in Portuguese: `Dado / Quando / Então`).
_Avoid_: test cases, requirements.

**Reference**:
The ground-truth User Story stored under `outputs.reference` for each dataset
example. Every metric is judged by similarity to it — it is the target, not a hint.
_Avoid_: expected answer, ground truth (use "Reference" in prose).

## Prompt Hub

**Prompt Hub**:
The LangSmith hosted registry of prompts. For evaluation it is the **single source
of truth**: `evaluate.py` pulls `v2` from the Hub, never from the local YAML, so a
push is a hard prerequisite for any score.

**Hub Handle**:
The account's public username on the Prompt Hub (`USERNAME_LANGSMITH_HUB`), forming
the prompt path `<handle>/bug_to_user_story_v2`. Created once in the LangSmith UI.
_Avoid_: account name, org id.

**v1 / v2**:
`v1` is the original low-quality starting prompt this project **pulls from the Hub**
(`leonanluppi/bug_to_user_story_v1`) — the entry point of the flow, shown as evidence but never
re-evaluated.
`v2` is the optimized prompt this project authors and publishes under the user's own Handle
(`<handle>/bug_to_user_story_v2`). It is the **only** prompt the challenge evaluates, and it
passes all five metrics ≥ 0.8 (see ADR-0005).

## Evaluation

**Base Metric**:
A metric `evaluate.py` actually computes via LLM-as-judge against the Reference:
`f1_score`, `clarity`, `precision`. These three are the only levers that matter.

**Derived Metric**:
`helpfulness` and `correctness` — never measured directly, only averaged from Base
Metrics (`helpfulness = (clarity + precision) / 2`, `correctness = (f1 + precision) / 2`).
Consequence: **Precision is the linchpin** — it weighs into both Derived Metrics.

**Approval**:
The pass condition: *all five* metrics ≥ 0.8 individually (not just the average).

**Experiment**:
A LangSmith evaluation run over the dataset that attaches per-example feedback scores,
visible in the Experiments tab. Produced by the additive `run_experiment.py` (via
`langsmith.evaluation.evaluate()`), **not** by the immutable `evaluate.py`. See ADR-0003.
_Avoid_: test run.

**v1 → v2 narrative**:
The deliverable's story is `v1` (the initial prompt pulled from the Hub, low quality) → `v2`
(the optimized prompt this project authors) → evaluate `v2` / iterate. Only `v2` is formally
evaluated, so there is **no** side-by-side LangSmith Comparison View; the evidence is the single
scored `v2` Experiment plus traces of ≥ 3 examples.
