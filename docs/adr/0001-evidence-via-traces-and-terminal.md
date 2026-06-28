# Evaluation evidence comes from traces + terminal, not a native LangSmith Experiment

The deliverable asks for "avaliações no dashboard com notas ≥ 0.8", but `evaluate.py`
is immutable and only prints scores to the terminal, creates/loads the eval dataset,
and emits traces via `LANGSMITH_TRACING=true`. It never calls `langsmith.evaluation.evaluate()`
or `create_feedback`, so it produces **no native Experiment** with per-example scores in
the dashboard's Experiments tab. We accept **dataset + traces + a terminal screenshot of
the ✅ APPROVED output** as the evidence of record.

## Considered Options

- **Add `src/run_experiment.py`** calling `evaluate()` to generate a real Experiment.
  Rejected for now: goes beyond the SPEC's fixed file structure and is unnecessary if the
  course accepts traces. Revisit only if grading explicitly requires an Experiment.
- **Modify `evaluate.py`** to emit feedback — rejected: the file is declared immutable.

## Consequences

- "Done" is proven by a real run (all five metrics ≥ 0.8 in the terminal) plus LangSmith
  traces of ≥ 3 examples and the 15-example dataset — not by an Experiments-tab artifact.
- If the course later demands a native Experiment, the workaround (`run_experiment.py`)
  is additive and does not touch the immutable files. Superseding this ADR is cheap.
