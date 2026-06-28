# The v2 prompt emits only the User Story; Chain-of-Thought stays internal

Every Base Metric (`f1_score`, `clarity`, `precision`) is an LLM-as-judge comparison of the
model's *entire* output against the `reference`, which is just the User Story. Any visible
reasoning preamble ("vou pensar passo a passo…") counts as content absent from the reference,
so it is penalised as unnecessary/extra information — and **Precision is the linchpin** (it
feeds both Derived Metrics). Therefore the v2 prompt instructs the model to reason **silently
/ internally** and output **only** the final formatted User Story (`Como um… eu quero… para
que…` + `Critérios de Aceitação` in `Dado/Quando/Então`), with no preamble, no explanation,
no fences.

## Consequences

- Chain-of-Thought is still claimed and applied as an internal technique, but must never
  surface in the answer. The output-format rule in `system_prompt` is load-bearing.
- This is a deliberate deviation from the naive "make the model show its reasoning" reading
  of the SPEC's CoT hint. A reviewer who "fixes" the prompt to print the reasoning will tank
  precision/f1 — hence this record.
