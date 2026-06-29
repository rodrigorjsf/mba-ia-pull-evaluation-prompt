# Native LangSmith Experiments via an additive `evaluate()` runner

**Supersedes [ADR-0001](./0001-evidence-via-traces-and-terminal.md).**

The SPEC deliverable (§2B "Resultados Finais" and §3 "Evidências no LangSmith") asks for a
public dashboard link **showing the evaluations**, screenshots of scores ≥ 0.8, and a
**comparative table**. `evaluate.py` is immutable and only prints scores to the terminal and
emits traces via `LANGSMITH_TRACING=true` — it never calls `langsmith.evaluation.evaluate()`
or `create_feedback`, so the dashboard has **no scored Experiment**.
ADR-0001 deferred the fix and accepted traces + a terminal screenshot. We now treat the
dashboard-visible scores + native comparison as a **hard deliverable**, which supersedes that
decision.

## Decision

Add an **additive** `run_experiment.py` (repo root, sibling of `evaluate_throttled.py`) that:

- calls `langsmith.evaluation.evaluate()`,
- wraps the three Base Metrics from `metrics.py` (`f1_score`, `clarity`, `precision`) as
  LangSmith evaluators, deriving `helpfulness` and `correctness` from them,
- targets the optimized prompt **pulled from the Hub** (`v2`) over the existing eval dataset,
- reuses the `InMemoryRateLimiter` throttle (`install_rate_limiter`) so the Gemini free tier
  does not 429.

Result: **a scored `v2` Experiment** with per-example feedback scores → the Experiments tab
showing all five metrics ≥ 0.8 plus traces of the evaluated examples in the dashboard. (The
deliverable evaluates only `v2`; see [ADR-0004](./0004-evaluate-only-v2.md).)

The immutable files (`evaluate.py`, `metrics.py`, `utils.py`) stay untouched, and
`evaluate_throttled.py` remains the SPEC's **official terminal pass** for v2. The new runner
is evidence tooling, not a replacement evaluator.

## Considered Options

- **Modify `evaluate.py`** to emit feedback — rejected: declared immutable.
- **`create_feedback` on the traces** produced by `evaluate.py` — rejected: no native
  Experiment object, so the scores never form a dashboard Experiment.
- **Keep traces + terminal only** (ADR-0001) — rejected: the scores never appear *in the
  dashboard*, which is what §3 asks for.

## Consequences

- The dashboard shows the scored `v2` Experiment + traces of ≥ 3 examples. There is no native
  Comparison View — only `v2` is evaluated (see [ADR-0004](./0004-evaluate-only-v2.md)).
- The judge is the SPEC-locked **`gpt-4o`** (generation `gpt-4o-mini`), run **sequentially** so
  the 30k-TPM cap never 429s and zeroes a metric; the Gemini free tier stays a throttled
  fallback. Experiment scores match the `evaluate_throttled.py` terminal run.
- `run_experiment.py` is a code change → it is under the repo's `/tdd` mandate and ships with
  a test (mirroring `tests/test_evaluate_throttled.py`).
- `evaluate()` may parallelise examples; the shared rate limiter still paces globally, and
  `max_concurrency` is kept low.
