# Failing baseline = a crafted `v0` (real run); `v1` stays illustrative

> **Status: SUPERSEDED by [ADR-0005](./0005-evaluate-only-v2.md).**
> The `v0` failing-baseline approach was abandoned. The deliverable now evaluates **only the
> optimized `v2`** (which passes all five metrics ≥ 0.8 under the SPEC-locked `gpt-4o-mini`
> generation / `gpt-4o` judge). The text below is kept verbatim as the historical record of the
> decision that was reversed — no `v0` prompt, Experiment, or comparison table ships.

The SPEC narrative is "a bad prompt fails, the optimized one passes", and the deliverable is
stronger when the dashboard actually shows the evaluator **catching a bad prompt**. But a real
evaluation of the original `v1` (`leonanluppi/bug_to_user_story_v1`) scores **0.8748 —
APPROVED, above v2's 0.8277** under the free Gemini judge: the judge is lenient and the
bug→story task is easy, so even a vague prompt writes a decent story. `v1` therefore **cannot**
serve as a real failing example.

## Decision

Introduce **`bug_to_user_story_v0`** — a *deliberately* under-optimized prompt (no persona, no
few-shot, no explicit format rules) authored to genuinely **REPROVAR** under the same
evaluator — published publicly to `<handle>/bug_to_user_story_v0` and evaluated as a real
Experiment.

The README "Resultados Finais" comparative table has **three columns**:

| Column | Source | Status |
|--------|--------|--------|
| **v0** | **real** run (this project) | REPROVADO |
| **v1** | **illustrative** — the SPEC's fictitious numbers (0.45 / 0.52 / 0.48 / 0.50 / 0.46) | REPROVADO |
| **v2** | **real** run (this project) | APROVADO (0.8277) |

The dashboard **Comparison View is `v0` vs `v2`** (both real). `v1` is **not re-run**; it
appears only in the README table, explicitly labelled as the SPEC's illustrative values.

## Considered Options

- **Real `v1` run** — rejected: it passes (0.87), contradicting the "bad vs good" story.
- **Stronger `gpt-4o` judge** to make `v1` fail — rejected: cost (~US$1-5) and no guaranteed
  failure on an easy task.
- **Drop the failing case** (v1 illustrative only) — rejected: weakens the evidence; the
  SPEC's own v1 numbers are fictitious, whereas a real failing `v0` is stronger proof.

## Consequences

- Honest, **real** failing evidence (`v0`) alongside an SPEC-faithful **illustrative** `v1`.
- The README **must** label the `v1` column as illustrative / from the SPEC, never as a real
  run — otherwise the table is misleading.
- `v0` must be **verified to actually fail** at run time; if it stubbornly passes under the
  lenient judge, degrade it further (break the output format / starve the structure) before
  publishing.
- This **adds** `v0` rather than re-running `v1`, so the prior "keep v1 illustrative, don't
  re-run it" decision still holds.
