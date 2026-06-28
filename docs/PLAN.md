# Implementation Plan — Pull / Optimize / Evaluate Prompts

Planning output of a `grill-with-docs` session against [`docs/SPEC.md`](./SPEC.md).
Glossary: [`CONTEXT.md`](../CONTEXT.md). Decisions: [`docs/adr/`](./adr/).

## Locked decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Provider = Gemini** (`gemini-2.5-flash` for both answer and eval) | User has the Google key; free tier. |
| D2 | **Pragmatic TDD**: the 6 SPEC tests rigorously; `pull`/`push` with light mocked-`hub` unit tests | They are thin `hub` + I/O wrappers ([`CLAUDE.md`](../CLAUDE.md) mandates `/tdd` for `src/`). |
| D3 | ~~**Evidence = dataset + traces + terminal screenshot** (no native Experiment)~~ **Superseded by D9 / ADR-0003** | The deliverable does require dashboard-visible scores. |
| D4 | **`v2.yml` flat** (top-level keys, not nested under `bug_to_user_story_v2:`) | `utils.validate_prompt_structure` reads top-level `description`/`system_prompt`/`version`/`techniques_applied`. |
| D5 | **Single template var `{bug_report}`**: `system_prompt` = persona+rules+few-shot (no var), `user_prompt` = `"{bug_report}"` | `evaluate.py` calls `chain.invoke({"bug_report": ...})`; any other required var errors on all 15. |
| D6 | **Output = the User Story only** (CoT internal, no preamble) | The judged answer is compared whole against `reference`. See ADR-0002. |
| D7 | **Techniques = Few-shot + Role + CoT** (`techniques_applied` lists 3 ≥ 2) | SPEC requires Few-shot + ≥1; `test_minimum_techniques` requires ≥2 in metadata. |
| D8 | **Escape `{{ }}`** if any few-shot text contains literal braces | `ChatPromptTemplate` f-string treats `{x}` as a variable. |

**Precision is the linchpin** — it weighs into both Derived Metrics, so optimise for
factual fidelity to `reference` above all (see `CONTEXT.md`).

## Build sequence (each `src/` file via `/tdd`)

```mermaid
flowchart TD
    classDef setup fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef code fill:#2d4a2b,stroke:#5cb85c,color:#fff
    classDef artifact fill:#5f4b1e,stroke:#d9a44a,color:#fff
    classDef loop fill:#5f1e3a,stroke:#d94a90,color:#fff

    W0["W0 · Setup<br/>venv + pip install<br/>.env (Gemini) + Hub handle"]:::setup
    W1["W1 · pull_prompts.py<br/>hub.pull v1 → save_yaml"]:::code
    W2["W2 · v2.yml + 6 SPEC tests<br/>red → green, no creds<br/>CORE DELIVERABLE"]:::artifact
    W3["W3 · push_prompts.py<br/>build ChatPromptTemplate<br/>hub.push public=True"]:::code
    W4["W4 · End-to-end loop<br/>pull → push → evaluate<br/>iterate until 5×5 ≥ 0.8"]:::loop
    W5["W5 · README + evidence"]:::artifact

    W0 --> W1 --> W2 --> W3 --> W4 --> W5
    W4 -.->|metric < 0.8| W2
    e1@{ animate: true }
```

- **W0 — Setup (non-code).** `venv` + `pip install -r requirements.txt`; create `.env` from
  `.env.example` (Gemini key, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`,
  `USERNAME_LANGSMITH_HUB`); create the Hub handle once in the LangSmith UI.
- **W1 — `pull_prompts.py`.** Red test with mocked `hub.pull` → impl: connect,
  `hub.pull("leonanluppi/bug_to_user_story_v1")`, extract system/user message templates,
  `save_yaml` to `prompts/bug_to_user_story_v1.yml`.
- **W2 — `v2.yml` + the 6 tests (core).** Write the 6 tests first (red), then author
  `v2.yml` to green. Flat schema: `description`, `system_prompt` (persona + explicit rules +
  few-shot + Markdown/User-Story format demand), `user_prompt: "{bug_report}"`,
  `version: "v2"`, `techniques_applied: [Few-shot, Role, CoT]`, `tags`, `created_at`. Must
  also satisfy `utils.validate_prompt_structure`. Runs with **no credentials**.
- **W3 — `push_prompts.py`.** Red test with mocked `hub.push` → impl: `load_yaml(v2)`,
  validate, build `ChatPromptTemplate.from_messages([("system", …), ("human", "{bug_report}")])`,
  `hub.push(f"{handle}/bug_to_user_story_v2", tmpl, new_repo_is_public=True,
  new_repo_description=…, tags=…)`. Verify the exact `hub.push` signature at implementation
  time (package not yet installed).
- **W4 — End-to-end loop.** `pull → push → evaluate`; read scores; tune `v2.yml`; repeat
  3–5×. Credentials required here.
- **W5 — README + evidence.** The final `README.md` is written **entirely in Brazilian
  Portuguese** (per user instruction — overrides the global "durable artifacts in English"
  rule for this file; it is an MBA deliverable and the SPEC is already pt-BR). Sections A
  (techniques + justification + examples), B (results: dashboard link, screenshots,
  v1-vs-v2 table), C (how to run). Capture the 15-example dataset, traces of ≥ 3 examples,
  and the ✅ terminal screenshot.

## Risks

- **Gemini 429 on a judge call → score 0.0 → fails** (it is scored as zero, not skipped).
  `evaluate.py` is immutable (no backoff) → mitigate by pacing runs and re-running.
- **`pull` overwrites the committed `v1.yml`** — confirm the regenerated format matches the
  existing artifact, or accept the regeneration.
- **`docs/ROADMAP.md` absent** while `CLAUDE.md` asks for README↔ROADMAP sync — decide in W5
  whether to add a minimal one.

## What stays untouched

`src/evaluate.py`, `src/metrics.py`, `src/utils.py`, `datasets/bug_to_user_story.jsonl` —
declared ready/immutable by the SPEC. The plan works within their contract.

---

## Slice 6 — Dashboard Experiments + `v0` failing baseline

Planning output of a second `grill-with-docs` session: the SPEC's "dashboard mostrando as
avaliações" + "tabela comparativa v1 vs v2" were only partially met — the v2 run printed to
the terminal (no scored Experiment in the dashboard), and no real failing prompt was ever
evaluated. This slice closes both gaps.

### Locked decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D9 | **Native Experiments** via an additive `run_experiment.py` calling `langsmith.evaluation.evaluate()` (supersedes D3) | Only way to put scores **in the dashboard** + get a native Comparison View. See ADR-0003. |
| D10 | **Failing baseline = a crafted `v0`** (real run, REPROVADO); `v1` is **not** re-run | A real `v1` run scores 0.87 (passes) under the free judge. See ADR-0004. |
| D11 | **README table = v0 × v1 × v2**: v0 real, **v1 = SPEC's illustrative numbers (labelled)**, v2 real | User decision; honours the SPEC narrative without exposing the weak-judge 0.87. |
| D12 | **Judge stays Gemini free** (`gemini-3.1-flash-lite` + 14 RPM throttle) for every run | Zero cost; keeps v2 consistent with the existing 0.8277; reuse `install_rate_limiter`. |
| D13 | **Hub = two prompts**: `<handle>/bug_to_user_story_v0` (bad) + `…_v2` (good), both public | No deletion of the existing public v2, no commit-order problem. |
| D14 | **Reuse the existing eval dataset**, add 2 Experiments; **inventory read-only first**, no blind wipe | The old v2 "result" was traces only; new Experiments supersede it. Preserves the public dataset link. |

### Build sequence (each code file via `/tdd`)

```mermaid
flowchart TD
    classDef setup fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef code fill:#2d4a2b,stroke:#5cb85c,color:#fff
    classDef artifact fill:#5f4b1e,stroke:#d9a44a,color:#fff
    classDef loop fill:#5f1e3a,stroke:#d94a90,color:#fff

    S0["S0 · Read-only inventory<br/>datasets / prompts / experiments<br/>(refresh creds if 401)"]:::setup
    S1["S1 · prompts/bug_to_user_story_v0.yml<br/>deliberately under-optimized"]:::artifact
    S2["S2 · push v0 (public)<br/>generalize push_prompts.py via /tdd"]:::code
    S3["S3 · run_experiment.py<br/>evaluate() + metrics.py + throttle<br/>2 Experiments (v0, v2)"]:::code
    S4["S4 · Verify v0 REPROVA & v2 APROVA<br/>iterate v0 if it still passes"]:::loop
    S5["S5 · README + evidence<br/>v0×v1×v2 table, comparison link, screenshots"]:::artifact

    S0 --> S1 --> S2 --> S3 --> S4 --> S5
    S4 -.->|v0 passes| S1
    e1@{ animate: true }
```

- **S0 — Inventory (non-code, read-only).** List datasets / my Hub prompts / Experiments to
  confirm what exists before adding anything. No deletes. (Partial inventory already confirmed at
  planning time: the dataset `mba-project-evaluation-prompt-eval` with 15 examples exists and the
  key authenticates.) Helper scripts run outside the repo must load `.env` by explicit path —
  `find_dotenv()` walks up from the *script* file, so a script in `/tmp` finds no `.env`.
- **S1 — `prompts/bug_to_user_story_v0.yml`.** A deliberately under-optimized prompt: no persona,
  no few-shot, no format rules — engineered to break output structure so the judge scores it
  below 0.8. Flat schema like v2 so `push_prompts.py` can load it.
- **S2 — Push `v0` public.** Generalize `push_prompts.py` (deliverable, via `/tdd`) to push an
  arbitrary version → `<handle>/bug_to_user_story_v0`, `new_repo_is_public=True`.
- **S3 — `run_experiment.py` (root, via `/tdd`).** `evaluate()` with the 3 Base Metrics from
  `metrics.py` as evaluators (+ derived), targets `v0` and `v2` pulled from the Hub over the
  existing dataset, reuses `install_rate_limiter`, low `max_concurrency`. One Experiment each.
- **S4 — Verify the contrast.** Confirm `v0` REPROVA (≥ 1 metric < 0.8) and `v2` APROVA
  (all 5 ≥ 0.8). If `v0` stubbornly passes, degrade it further and re-push.
- **S5 — README + evidence.** Replace the `a anexar` placeholders: the **v0 × v1 × v2** table
  (v1 column flagged as the SPEC's illustrative values), the public **Comparison View** link,
  and screenshots of the scored Experiments + ≥ 3 traces. Keep `evaluate_throttled.py` documented
  as the official v2 terminal pass.

### Risks

- **`v0` passes the lenient judge** — the easy task + content-overlap metrics may rescue a bad
  prompt. Mitigate by breaking the output *shape* (one-liner, no acceptance criteria) so F1
  recall and Clarity collapse; verify before publishing (S4 loop).
- **`evaluate()` + Gemini free 429** — the shared `InMemoryRateLimiter` must wrap the evaluator
  LLMs too; keep `max_concurrency` low so the global pace holds.
- **`.env` loading from helper scripts** — the credential is valid (auth confirmed at planning
  time). A planning-time 401 was a verification-script artifact: `load_dotenv()`/`find_dotenv()`
  search from the *script's* directory, so a script in `/tmp` loads no key. Real scripts run from
  the repo root (e.g. `run_experiment.py`) and authenticate fine; any throwaway diagnostic must
  pass the `.env` path explicitly or `os.chdir` to the repo root.
- **Public visibility** — each LangSmith resource (prompts, dataset, Experiments/project) must
  be shared individually for the public links to resolve.

### What stays untouched (unchanged from above)

`src/evaluate.py`, `src/metrics.py`, `src/utils.py`, `datasets/bug_to_user_story.jsonl`. The new
`run_experiment.py` is additive; `evaluate_throttled.py` remains the official v2 terminal pass.
