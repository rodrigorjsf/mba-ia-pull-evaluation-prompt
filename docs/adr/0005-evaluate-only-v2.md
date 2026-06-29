# Evaluate only the optimized `v2`; drop the `v0` failing baseline

**Supersedes [ADR-0004](./0004-v0-failing-baseline-v1-illustrative.md).**

ADR-0004 introduced a deliberately under-optimized `v0` prompt as a *real* failing baseline, so
the dashboard would show the evaluator catching a bad prompt and the README could carry a
`v0 × v1 × v2` comparison. That approach is abandoned.

Under the SPEC-locked models (generation `gpt-4o-mini`, judge `gpt-4o`) the optimized **`v2`
now passes all five metrics ≥ 0.8** (mean 0.8394, reproduced across two independent sequential
Experiments). The challenge only asks to evaluate the optimized prompt, so a manufactured
failing baseline adds maintenance and narrative noise without strengthening the deliverable.

## Decision

The deliverable evaluates **only `v2`**. There is no `v0` prompt, no `v0` Experiment, and no
`v0` column in the README.

- The narrative is **`v1` (the initial prompt pulled from the Hub, `leonanluppi/bug_to_user_story_v1`)
  → `v2` (the optimized prompt this project authors and publishes) → evaluate `v2` / iterate**.
- `v1` is shown only as the starting point (the pulled prompt), never re-evaluated.
- `run_experiment.py` accepts `v2` only (`ALLOWED_VERSIONS = ("v2",)`); the version switch is
  retained as a single-value seam, not a `v0`/`v2` selector.
- `src/evaluate.py` / `evaluate_throttled.py` remain the SPEC's official terminal pass for `v2`.

## Considered Options

- **Keep the `v0` baseline** (ADR-0004) — rejected: now that `v2` passes under the rigorous
  `gpt-4o` judge, the contrast no longer needs a synthetic failing prompt; `v0` only adds a
  prompt, a public Hub artifact, an Experiment, and table columns to maintain.
- **Re-run `v1` as the failing case** — rejected: a real `v1` run passes (~0.87) under the
  lenient free judge, so it is not a reliable failing example, and the rigorous judge was never
  budgeted to force it to fail.

## Consequences

- Cleaner, honest narrative: one optimized prompt, evaluated, passing — no manufactured baseline.
- The dashboard evidence is the single scored `v2` Experiment (`bug_to_user_story_v2-765f0d5e`)
  plus traces of ≥ 3 examples; there is no native two-Experiment Comparison View.
- ADR-0003 still holds for *how* the scored Experiment reaches the dashboard (the additive
  `run_experiment.py`); only its `v0`-vs-`v2` framing is dropped.
- The `v0` prompt was never committed to `development`, so no code or prompt deletion is needed
  here — this ADR records the reversal and removes the lingering `v0` language from the docs.
