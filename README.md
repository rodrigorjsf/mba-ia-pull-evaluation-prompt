# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Pipeline que puxa um prompt de baixa qualidade do **LangSmith Prompt Hub**, o
refatora com técnicas de Prompt Engineering, republica a versão otimizada de forma
pública e a avalia automaticamente contra 15 cenários reais usando 5 métricas via
**LLM-as-Judge**.

> **Status:** ✅ **APROVADO** — todas as 5 métricas ≥ 0.8 (média geral **0.8277**).
> Prompt otimizado: [`rodrigorjsf/bug_to_user_story_v2`](https://smith.langchain.com/prompts/bug_to_user_story_v2).

O fluxo completo é `pull (v1) → otimizar → push público (v2) → avaliar → iterar`.

```mermaid
flowchart LR
    Hub[("LangSmith<br/>Prompt Hub")]
    V1["📥 v1 RUIM<br/>leonanluppi/bug_to_user_story_v1"]
    OPT["🛠️ Otimização<br/>Few-shot · Role · Structured Output"]
    V2["📤 v2 OTIMIZADO<br/>rodrigorjsf/bug_to_user_story_v2"]
    EVAL["⚖️ evaluate.py<br/>15 exemplos × 3 juízes LLM"]
    GATE{"Todas as 5<br/>métricas ≥ 0.8?"}
    DONE["✅ APROVADO<br/>média 0.8277"]

    Hub e1@--> V1
    V1 e2@--> OPT
    OPT e3@--> V2
    V2 e4@--> Hub
    Hub e5@--> EVAL
    EVAL e6@--> GATE
    GATE -->|"não · itera"| OPT
    GATE -->|sim| DONE

    e1@{ animate: true }
    e2@{ animate: true }
    e3@{ animate: true }
    e4@{ animate: true }
    e5@{ animate: true }
    e6@{ animate: true }

    classDef bad  fill:#ffe1e1,stroke:#d33,color:#900
    classDef good fill:#e1f7e1,stroke:#2a2,color:#070
    classDef proc fill:#e7efff,stroke:#36c,color:#024
    classDef hub  fill:#fff4d6,stroke:#e6a700,color:#6b4f00
    class V1 bad
    class V2,DONE good
    class OPT,EVAL proc
    class Hub hub
```

---

## Como Executar

### Pré-requisitos

- **Python 3.12** (as dependências fixadas — `pydantic-core`, stack LangChain — ainda
  não têm wheels para 3.13/3.14).
- Conta no [LangSmith](https://smith.langchain.com/) (para o Prompt Hub e o tracing).
- Uma API Key de LLM: **Google Gemini** (free) ou **OpenAI**.

### 1. Ambiente e dependências

```bash
# com uv (recomendado)
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# ou com venv padrão
python3.12 -m venv .venv
source .venv/bin/activate        # fish: source .venv/bin/activate.fish · Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Credenciais (`.env`)

Copie `.env.example` para `.env` e preencha:

```bash
LANGSMITH_API_KEY=...            # sua chave do LangSmith
USERNAME_LANGSMITH_HUB=...       # seu handle no Hub (namespace do push)
LANGSMITH_PROJECT=mba-project-evaluation-prompt

# Provider de LLM (escolha um)
LLM_PROVIDER=google              # ou "openai"
GOOGLE_API_KEY=...               # se google
LLM_MODEL=gemini-3.1-flash-lite  # modelo que responde
EVAL_MODEL=gemini-3.1-flash-lite # modelo juiz (avaliação)
```

### 3. Ordem de execução

> Use o **python do venv** (`.venv/bin/python`) — não existe comando `python` puro sem
> ativar o venv. Como alternativa, ative-o antes (fish: `source .venv/bin/activate.fish`) e
> use `python` direto.

```bash
# 1. Pull do prompt inicial (v1) do Hub -> prompts/bug_to_user_story_v1.yml
.venv/bin/python src/pull_prompts.py

# 2. Refatorar: editar prompts/bug_to_user_story_v2.yml (já otimizado neste repo)

# 3. Push público do v2 -> {USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2
.venv/bin/python src/push_prompts.py

# 4. Avaliação end-to-end oficial (pass terminal do SPEC — puxo o v2 do Hub, 15 exemplos)
#    No free tier do Gemini, execute via o wrapper com throttling — MESMA lógica do
#    evaluate.py, só com pacing de RPM (ver "Nota sobre limites de taxa" abaixo):
.venv/bin/python evaluate_throttled.py
#    (com cota suficiente, o original imutável roda igual: .venv/bin/python src/evaluate.py)

# 5. (Opcional) Experimento nativo LangSmith — Comparison View v0 vs. v2
#    Registra um Experiment LangSmith para v0 (baseline REPROVADO) e v2 (APROVADO)
#    e gera o link público de Comparison View para comparar métricas dos dois runs:
.venv/bin/python run_experiment.py
```

### 4. Testes de validação (sem credenciais)

```bash
.venv/bin/python -m pytest -q
```

### Nota sobre limites de taxa (rate limit) e conformidade com o SPEC

O `src/evaluate.py` dispara ~60 chamadas ao LLM por execução (15 exemplos × 1 geração +
3 juízes). Em **cota free** do Gemini, esse burst estoura o limite por minuto do
`gemini-3.1-flash-lite`, recebe `429` e o `evaluate.py` **descarta exemplos silenciosamente**
(resposta vazia → pulada), corrompendo as notas.

> **Conformidade com o SPEC.** Para respeitar o enunciado, **`src/evaluate.py` NÃO foi
> modificado** — permanece exatamente como no boilerplate (arquivo imutável). Foi necessário
> criar [`evaluate_throttled.py`](evaluate_throttled.py), e **foi ele o efetivamente
> executado** para gerar as evidências, devido às políticas atuais do Gemini e à limitação de
> rate limit do modelo usado (`gemini-3.1-flash-lite`, 15 RPM no free tier). A **lógica
> seguida é exatamente a mesma do `evaluate.py` original**: o wrapper apenas injeta um
> `InMemoryRateLimiter` (~14 RPM) em toda instância de `ChatGoogleGenerativeAI` (gerador +
> juízes) e executa o `src/evaluate.py` imutável via `runpy`. Nenhuma métrica, prompt ou
> regra de aprovação é alterada — só o ritmo das chamadas à API.

```bash
# roda o evaluate.py ORIGINAL com pacing de ~14 RPM (zero 429, 15/15 limpos)
.venv/bin/python evaluate_throttled.py
```

Alternativa: com cota maior (tier pago ou modelo com RPM mais alto), o original imutável roda
igual — `.venv/bin/python src/evaluate.py`.

---

## Técnicas Aplicadas (Fase 2)

O prompt otimizado (`prompts/bug_to_user_story_v2.yml`) combina **três técnicas**
(declaradas em `techniques_applied`). O diagrama abaixo contrasta cada defeito intencional
do v1 com a correção correspondente no v2:

```mermaid
flowchart TB
    subgraph V1G["❌ v1 — Prompt RUIM (ponto de partida)"]
        direction TB
        a1["Sem persona definida"]
        a2["{bug_report} duplicado<br/>no system + no user"]
        a3["Instrução vaga:<br/>'crie uma user story'"]
        a4["Zero exemplos"]
        a5["Sem formato de saída exigido"]
    end
    subgraph V2G["✅ v2 — Prompt OTIMIZADO (entregável)"]
        direction TB
        b1["Persona: Product Manager sênior<br/>→ Role Prompting"]
        b2["user_prompt = só {bug_report};<br/>conhecimento todo no system"]
        b3["6 regras explícitas<br/>+ tratamento de edge cases"]
        b4["2 exemplos bug→story<br/>→ Few-shot Learning"]
        b5["Formato Markdown fixo<br/>→ Structured Output"]
    end
    a1 -. otimiza .-> b1
    a2 -. otimiza .-> b2
    a3 -. otimiza .-> b3
    a4 -. otimiza .-> b4
    a5 -. otimiza .-> b5

    classDef bad  fill:#ffe1e1,stroke:#d33,color:#900
    classDef good fill:#e1f7e1,stroke:#2a2,color:#070
    class a1,a2,a3,a4,a5 bad
    class b1,b2,b3,b4,b5 good
```

### 1. Role Prompting

O `system_prompt` abre fixando uma persona especialista:

```
Você é um Product Manager sênior especialista em metodologias ágeis e descoberta de produto.
```

**Por quê:** ancorar o modelo no papel de PM faz com que ele traduza o **sintoma técnico**
do bug em uma **necessidade de negócio** do usuário afetado — exatamente o que a User Story
de referência espera — em vez de apenas reescrever o relato do bug.

### 2. Few-shot Learning (obrigatório)

Dois exemplos completos `bug → User Story` embutidos no `system_prompt`, com cenários
**novos** (videoconsulta de telemedicina; cronômetro de quiz em EdTech) que **não** se
sobrepõem aos 15 itens do dataset de avaliação (evita contaminação).

**Por quê:** demonstrar o formato exato exigido —
`Como um… eu quero… para que…` seguido de `Critérios de Aceitação` em
`Dado / Quando / Então` — reduz drasticamente a variância de formato e eleva o **recall**
(F1), porque a resposta passa a cobrir os critérios no mesmo padrão da referência.

### 3. Structured Output Formatting

Regras explícitas exigindo **apenas** a User Story final, sem raciocínio visível
([ADR-0002](docs/adr/0002-output-is-user-story-only.md)):

```
Escreva APENAS a User Story final — sem explicações, sem raciocínio, sem texto introdutório.
```

**Por quê:** os juízes de **Precision** e **Clarity** penalizam alucinação, divagação e
verbosidade. Forçar saída focada e concisa, sem etapas intermediárias, protege essas duas
métricas (e, por consequência, as derivadas Helpfulness e Correctness). O raciocínio (Chain
of Thought) é mantido **interno** ao modelo — aplicado, mas nunca impresso — justamente para
não poluir a saída avaliada.

> O `user_prompt` é exatamente `"{bug_report}"` — a única variável de template; todo o
> conhecimento (persona, regras, exemplos) vive no `system_prompt`.

---

## Resultados Finais

### Tabela comparativa v0 × v1 × v2

> **v0** e **v2** são runs reais (via `run_experiment.py`). **v1** é ilustrativo do SPEC —
> não é um run real e não segue as fórmulas derivadas (ver
> [ADR-0004](docs/adr/0004-v0-failing-baseline-v1-illustrative.md)).
> Threshold de aprovação: todas as 5 métricas ≥ 0.8.

| Métrica | **v0** (real — REPROVADO) | **v1** (ilustrativo — SPEC) | **v2** (real — APROVADO ≥ 0.8) |
|---|---|---|---|
| f1_score | ⟨EVIDENCE: v0 f1_score⟩ | 0.48 | ⟨EVIDENCE: v2 f1_score⟩ |
| clarity | ⟨EVIDENCE: v0 clarity⟩ | 0.50 | ⟨EVIDENCE: v2 clarity⟩ |
| precision | ⟨EVIDENCE: v0 precision⟩ | 0.46 | ⟨EVIDENCE: v2 precision⟩ |
| helpfulness | ⟨EVIDENCE: v0 helpfulness⟩ | 0.45 | ⟨EVIDENCE: v2 helpfulness⟩ |
| correctness | ⟨EVIDENCE: v0 correctness⟩ | 0.52 | ⟨EVIDENCE: v2 correctness⟩ |
| **Status** | ❌ REPROVADO | — ilustrativo | ✅ APROVADO |

> **Nota v1:** valores do enunciado do SPEC reproduzidos literalmente para fins ilustrativos
> (ilustrativo — valores do SPEC, não é run real; não seguem as fórmulas derivadas).
> O v1 não foi re-executado — ver [ADR-0004](docs/adr/0004-v0-failing-baseline-v1-illustrative.md).

O **Comparison View público (v0 vs. v2)** gerado pelo `run_experiment.py`:
⟨EVIDENCE: comparison view url⟩

---

A **avaliação oficial do SPEC** (`evaluate_throttled.py` → `src/evaluate.py` imutável) mede
**apenas o prompt otimizado v2** — é o único prompt que o SPEC exige avaliar. O run abaixo
é **real** (`gemini-3.1-flash-lite`, 15/15 exemplos, throttle de 14 RPM), puxando o v2 do Hub.

### Avaliação real do v2 (entregável — pass terminal do SPEC)

#### Pull prompt inicial

`leonanluppi/bug_to_user_story_v1`:

<p align="center">
  <img src="docs/evidence/pull_prompt_evidence.png" alt="Prompt inicial" width="600px" />
</p>

`rodrigorjsf/bug_to_user_story_v2`:

#### Push prompt otimizado

<p align="center">
  <img src="docs/evidence/push_prompt_evidence.png" alt="Prompt otimizado" width="600px" />
</p>

#### Avaliação prompt otimizado

<p align="center">
  <img src="docs/evidence/evaluation_prompt_evidence.png" alt="Prompt evaluation" width="600px" />
</p>

### Evidências no LangSmith

- **Prompt v2 público:** <https://smith.langchain.com/hub/rodrigorjsf/bug_to_user_story_v2>
- **Dataset** [mba-project-evaluation-prompt-eval](https://smith.langchain.com/public/25221bb9-e549-43b0-9430-88edd1b9a4b6/d) com os 15 exemplos; tracing visível para todos.
- **Comparison View (v0 vs. v2):** ⟨EVIDENCE: comparison view url⟩

#### Exemplos — Comparison View (v0 vs. v2)

![Scores ≥ 0.8 no painel LangSmith — Comparison View v0 vs. v2](⟨EVIDENCE: screenshot scores⟩)

![Rastreamento de ≥ 3 exemplos no LangSmith](⟨EVIDENCE: screenshot traces⟩)

### Jornada de avaliação

O prompt v2 atingiu a aprovação **sem precisar de iteração de conteúdo** — o gargalo não
foi a qualidade do prompt, e sim a **cota de API**. Sequência real:

1. `gemini-2.5-flash` (free, ~5 RPM): só 6/15 exemplos avaliados; o restante caiu em `429`
   e foi descartado, com um juiz F1 zerado por rate-limit → medição corrompida.
2. `gemini-2.0-flash`: cota free `limit: 0` neste projeto → tudo 0.00.
3. `gemini-3.1-flash-lite` sem throttle: avançou para 8/15, ainda com 429.
4. `gemini-3.1-flash-lite` **com throttle de 14 RPM**: **15/15 limpos, zero 429 →
   APROVADO** (média 0.8277).

Lição alinhada ao tracing do LangSmith: distinga uma métrica derrubada a 0.0 por
**rate-limit** de um gap real de qualidade — reexecute com pacing antes de reescrever o
prompt.

---

## Métricas de avaliação

Os juízes (LLM-as-Judge, em `src/metrics.py`) produzem 3 métricas-base e 2 derivadas.
**Precision** é a métrica de maior alavancagem porque alimenta as duas derivadas:

```mermaid
flowchart LR
    subgraph J["🧑‍⚖️ Métricas Base — juízes LLM (metrics.py)"]
        F1["F1-Score<br/>precision/recall vs. referência"]
        CL["Clarity<br/>clareza, concisão, sem ambiguidade"]
        PR["Precision<br/>sem alucinação, foco, correção factual"]
    end
    HP["Helpfulness<br/>= (Clarity + Precision) / 2"]
    CO["Correctness<br/>= (F1 + Precision) / 2"]
    CL --> HP
    PR --> HP
    F1 --> CO
    PR --> CO

    classDef base  fill:#e7efff,stroke:#36c,color:#024
    classDef deriv fill:#ede1ff,stroke:#73c,color:#414
    classDef lever fill:#fff4d6,stroke:#e6a700,color:#6b4f00,stroke-width:3px
    class F1,CL base
    class PR lever
    class HP,CO deriv
```

| Métrica | Como é calculada |
|---|---|
| **F1-Score** | média harmônica de precision/recall da resposta vs. a referência |
| **Clarity** | organização, linguagem simples, ausência de ambiguidade, concisão |
| **Precision** | ausência de alucinação, foco na pergunta, correção factual |
| **Helpfulness** | derivada: `(Clarity + Precision) / 2` |
| **Correctness** | derivada: `(F1 + Precision) / 2` |

Aprovação exige **todas as 5 ≥ 0.8** (não apenas a média).

---

## Estrutura do projeto

```
mba-ia-pull-evaluation-prompt/
├── .env.example
├── requirements.txt
├── README.md
├── evaluate_throttled.py          # wrapper: roda o evaluate.py imutável com ~14 RPM
├── prompts/
│   ├── bug_to_user_story_v1.yml   # baseline puxado do Hub
│   └── bug_to_user_story_v2.yml   # prompt otimizado (entregável)
├── datasets/
│   └── bug_to_user_story.jsonl    # 15 bugs (5 simples, 7 médios, 3 complexos)
├── docs/
│   └── evidence/                  # saída bruta da avaliação real do v2
├── src/
│   ├── pull_prompts.py            # pull do Hub          (implementado)
│   ├── push_prompts.py            # push público do Hub  (implementado)
│   ├── evaluate.py                # avaliação            (imutável)
│   ├── metrics.py                 # 5 métricas           (imutável)
│   └── utils.py                   # helpers              (imutável)
└── tests/
    ├── test_prompts.py            # 6 testes de validação do v2
    ├── test_pull.py               # teste do pull (Hub mockado)
    └── test_push.py               # teste do push (Hub mockado)
```

> `src/evaluate.py`, `src/metrics.py`, `src/utils.py` e o dataset são **imutáveis** —
> nunca são editados. Os entregáveis implementados são os scripts de pull/push, o prompt
> v2 e os testes.

---

## Tecnologias

Python 3.12 · LangChain `0.3.13` · LangSmith `0.2.7` · Prompt Hub · pytest · prompts em
YAML · multi-provider (Google Gemini / OpenAI).
