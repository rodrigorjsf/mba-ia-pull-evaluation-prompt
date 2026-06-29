# Prompt Engineering Guide — Techniques Notes (bug → User Story optimization)

## Summary

We optimize a **single** `prompt_template | gpt-4o-mini` call that turns a Portuguese
bug report into an agile User Story ("Como um... eu quero... para que..." + "Critérios
de Aceitação" in Dado/Quando/Então), judged by `gpt-4o` against a hidden reference on
f1 / clarity / precision. clarity and precision already pass (~0.85–0.88); **f1
plateaus at ~0.78 and is the only bottleneck.** The root cause is not "a missing
technique" — it is a **recall ceiling under a precision constraint**: long references
(3600–5700 chars) carry many key points the answer must cover, and a see-saw means
adding content to lift recall-sub also drags precision-sub down (and vice-versa). So the
useful filter for every technique below is one question: **does it raise recall-sub
WITHOUT adding extraneous, ungrounded content?** Techniques that need extra model calls
(self-consistency, prompt-chaining, ToT search, ReAct, generated-knowledge, reflexion,
DSP) are flagged NOT directly usable in our locked single-call eval path; where a
legitimate single-call approximation exists, it is noted. The live single-call levers
are: **better few-shot exemplar selection, an in-call extract-then-write scratchpad, an
output schema that scales AC count to distinct behaviors, and a deletion-only
faithfulness pass.**

> **Honesty caveat.** Part of the recall gap on 5700-char references may be
> *irreducible*: if the reference contains detail that is simply not present in the bug
> report, no single-call prompt can recover it, and chasing it only burns precision.
> This bounds what any prompt change can deliver — the goal is to close the *recoverable*
> recall gap, not to hit a reference the input cannot support.

## Technique table

| Technique | Single-call viable? | How it could help our f1 (precision-sub / recall-sub) |
|---|---|---|
| **Zero-shot** | Yes | Baseline. gpt-4o-mini is instruction-tuned, but zero-shot leaves output *altitude/length/granularity* unspecified → under-covers long references (low recall). Not a fix on its own. |
| **Few-shot** | Yes | **Primary lever.** The page's real guidance is selection/format/distribution, not example *count*. Make exemplars themselves *complex* bugs with reference-granularity Dado/Quando/Então blocks → teaches the model the right output length/granularity for the failing 3600–5700-char cases → **raises recall** on hard cases without inviting padding on simple ones (precision held). |
| **Chain-of-Thought (CoT)** | Yes (single call) | Already tried as hidden/internal reasoning. Keep, but it does not by itself decide *coverage vs. concision* — pair it with an explicit enumeration step (see scratchpad) so the reasoning targets recall, not just correctness. |
| **Meta prompting** | Yes | Emphasizes structure/format over content. Use an abstract output schema/template (sections + "one Given/When/Then per distinct behavior") to **force coverage (recall)** while a fixed shape discourages free-floating padding (precision). |
| **Self-consistency** | **No** (needs N sampled paths + majority vote) | NOT usable: our eval path is one greedy call, no aggregation. No single-call approximation. |
| **Generated knowledge** | **No** in its 2-stage form (generate knowledge, then answer separately) | Single-call approximation = the **extract-then-write scratchpad**: in ONE response, first enumerate atomic requirements/scenarios from the bug, then write ACs from that list. This is where the technique's value survives in our constraint. |
| **Prompt chaining** | **No** (each subtask = a separate call) | NOT usable in eval. The intent (decompose → solve) is approximated single-call by the scratchpad (enumerate scenarios → emit one AC each). |
| **Tree of Thoughts (ToT)** | **No** for true ToT (generate+evaluate+search across calls) | Single-call approx exists (Hulbert "imagine three experts… each writes one step"), but it is **token-heavy and low-value on gpt-4o-mini** for a structured-extraction task — not recommended here. |
| **ReAct** | **No** (reason+act interleaved with external tool/observation calls) | NOT usable: no tools/retrieval in the eval path. |
| **Reflexion** | **No** (multi-trial: trajectory → eval → reflect → retry with memory) | NOT usable as designed. Single-trial cousin = self-refine (below). |
| **Self-refine** (Madaan 2023; not on the site index) | Yes, in a single call | Already tried as generic "internal self-refine." New angle: **narrow it to deletion-only** — a final in-call pass that DROPS any AC not grounded in the bug text. Acts as a **precision guard** so few-shot/scratchpad can push content harder. |
| **Least-to-most** (Zhou 2022; not on the site index) | **No** in canonical 2-stage form (decompose call, then solve call) | NOT directly usable. Its decomposition idea is absorbed by the single-call scratchpad (least → most = list sub-requirements, then resolve each into an AC). |
| **Step-back prompting** (Zheng 2023; not on the site index) | Partial (canonical form uses a separate abstraction call) | Single-call approximation: open with one in-call "step-back" line that states the *user goal / high-level principle* of the bug before writing — anchors the "Como um… para que…" and reduces off-target ACs (precision), mild recall help by framing scope. |
| **Directional Stimulus Prompting (DSP)** | **No** (needs a separately-trained policy LM to emit hints) | NOT usable: no second tunable model. The "hint" intuition is approximated by hand-written keyword/section cues in the static prompt (overlaps few-shot/meta). |
| **General tips / elements of a prompt** | Yes | Apply directly: clear action verb + `###` separators; be specific about *quantity and granularity* of ACs; **positive framing** (state what to include, not "don't omit"); the four elements (instruction / context / input data / output indicator) — make the *output indicator* an explicit Dado/Quando/Então schema. |

## Top recommendations to try next (ranked)

Each is a single `gpt-4o-mini` call; each is chosen to lift **recall-sub without adding
ungrounded content** (the precision side of the see-saw).

1. **Re-select few-shot exemplars to be complex, reference-granularity examples** —
   *highest confidence, lowest risk.* Replace "3–4 generic examples" with exemplars
   drawn from (or mirroring) the *hard* bugs: each demo's "Critérios de Aceitação"
   block should have the same number and depth of Dado/Quando/Então scenarios as a long
   reference. This teaches the model the correct output *altitude and length* for the
   3600–5700-char cases — directly attacking the recall ceiling on exactly the failing
   slice, while simple cases stay short (precision preserved). Lever = example
   selection/format/distribution, not example count.

2. **Add an in-call "extract-then-write" scratchpad** — *highest ceiling; attacks the
   see-saw coupling directly.* In one response: **Step A** — enumerate, from the bug
   text, every distinct behavior / requirement / edge case as an atomic bullet list;
   **Step B** — emit exactly one Given/When/Then per enumerated item, plus the
   "Como um… para que…" line. Because every AC is tied to a source fact, **recall rises
   (each behavior gets covered) while precision holds (nothing un-sourced is invented).**
   This is the legal single-call fusion of generated-knowledge / least-to-most /
   step-back. (Keep Step A out of the final answer if the judge penalizes visible
   reasoning — emit only Step B as the User Story.)

3. **Impose an output schema that scales AC count to the number of distinct behaviors**
   (meta-prompting + output-indicator). Instruct: "Write one acceptance criterion per
   distinct behavior or rule identified; do not merge two behaviors into one criterion
   and do not invent behaviors not in the report." Forces coverage (recall) and
   simultaneously discourages padding (precision) via the explicit "one-per-behavior,
   none-invented" rule.

4. **Deletion-only self-refine pass (faithfulness filter)** — single-call precision
   guard. After drafting, add a final in-call instruction: "Review each acceptance
   criterion; **delete** any criterion (or clause) not directly supported by the bug
   report. Do not add or reword." Narrowing self-refine to *deletion only* (vs. the
   general "improve" you already tried) lets recommendations #1–#3 push content
   aggressively, then trims the un-grounded tail that would otherwise cost precision-sub.

5. **One-line step-back goal statement** *(optional, low cost)*: begin the answer's
   reasoning with the user's high-level goal inferred from the bug, then write. Anchors
   the persona/benefit clause and keeps ACs on-scope (small precision help, mild recall
   framing). Cheap to bundle with #2.

> Net move: stack **#1 + #2 + #3** as the core (coverage-up, grounded), then **#4** as the
> trailing precision guard. This is the configuration most likely to break the see-saw
> because it raises recall via *source-grounded* content rather than free generation.

## Sources

- Techniques index — https://www.promptingguide.ai/techniques
- Zero-shot — https://www.promptingguide.ai/techniques/zeroshot
- Few-shot — https://www.promptingguide.ai/techniques/fewshot
- Chain-of-Thought — https://www.promptingguide.ai/techniques/cot
- Meta prompting — https://www.promptingguide.ai/techniques/meta-prompting
- Self-consistency — https://www.promptingguide.ai/techniques/consistency
- Generate knowledge — https://www.promptingguide.ai/techniques/knowledge
- Prompt chaining — https://www.promptingguide.ai/techniques/prompt_chaining
- Tree of Thoughts — https://www.promptingguide.ai/techniques/tot
- ReAct — https://www.promptingguide.ai/techniques/react
- Reflexion — https://www.promptingguide.ai/techniques/reflexion
- Directional Stimulus Prompting — https://www.promptingguide.ai/techniques/dsp
- General tips for designing prompts — https://www.promptingguide.ai/introduction/tips
- Elements of a prompt — https://www.promptingguide.ai/introduction/elements
- Least-to-most (not on the guide's index; canonical paper) — https://arxiv.org/abs/2205.10625
- Step-back prompting (not on the guide's index; canonical paper) — https://arxiv.org/abs/2310.06117
- Self-refine (not on the guide's index; canonical paper) — https://arxiv.org/abs/2303.17651
