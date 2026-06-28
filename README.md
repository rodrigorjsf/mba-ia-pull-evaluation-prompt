# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Pipeline que puxa um prompt de baixa qualidade do **LangSmith Prompt Hub**, o
refatora com técnicas de Prompt Engineering, republica a versão otimizada de forma
pública e a avalia automaticamente contra 15 cenários reais usando 5 métricas via
**LLM-as-Judge**.

> **Status:** ✅ **APROVADO** — todas as 5 métricas ≥ 0.8 (média geral **0.8277**).
> Prompt otimizado: [`rodrigorjsf/bug_to_user_story_v2`](https://smith.langchain.com/prompts/bug_to_user_story_v2).

O fluxo completo é `pull (v1) → otimizar → push público (v2) → avaliar → iterar`.

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
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Credenciais (`.env`)

Copie `.env.example` para `.env` e preencha:

```bash
LANGSMITH_API_KEY=...            # sua chave do LangSmith
USERNAME_LANGSMITH_HUB=...       # seu handle no Hub (namespace do push)
LANGSMITH_PROJECT=MBA-evaluation-prompt

# Provider de LLM (escolha um)
LLM_PROVIDER=google              # ou "openai"
GOOGLE_API_KEY=...               # se google
LLM_MODEL=gemini-2.5-flash       # modelo que responde
EVAL_MODEL=gemini-2.5-flash      # modelo juiz (avaliação)
```

### 3. Ordem de execução

```bash
# 1. Pull do prompt inicial (v1) do Hub -> prompts/bug_to_user_story_v1.yml
python src/pull_prompts.py

# 2. Refatorar: editar prompts/bug_to_user_story_v2.yml (já otimizado neste repo)

# 3. Push público do v2 -> {USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2
python src/push_prompts.py

# 4. Avaliação end-to-end (puxa o v2 do Hub, roda os 15 exemplos, imprime as métricas)
python src/evaluate.py
```

### 4. Testes de validação (sem credenciais)

```bash
.venv/bin/python -m pytest -q
```

### Nota sobre limites de taxa (rate limit)

O `src/evaluate.py` dispara ~60 chamadas ao LLM por execução (15 exemplos × 1 geração +
3 juízes). Em **cota free** do Gemini, esse burst pode estourar o limite por minuto,
receber `429` e **descartar exemplos silenciosamente** (resposta vazia → pulada),
corrompendo as notas. Duas saídas:

- Use um modelo com cota maior, ex. `gemini-3.1-flash-lite` (15 RPM / 500 RPD) em
  `LLM_MODEL`/`EVAL_MODEL`; **ou**
- Limite a taxa a ~14 RPM **sem alterar os arquivos imutáveis**, via um launcher externo
  que injeta um `InMemoryRateLimiter`:

```python
# run_throttled.py — roda o evaluate.py imutável com pacing de ~14 RPM
import runpy, sys
import langchain_google_genai as lcg
from langchain_core.rate_limiters import InMemoryRateLimiter
_lim = InMemoryRateLimiter(requests_per_second=14/60, check_every_n_seconds=0.5, max_bucket_size=1)
_orig = lcg.ChatGoogleGenerativeAI.__init__
lcg.ChatGoogleGenerativeAI.__init__ = lambda self, **kw: _orig(self, **{**kw, "rate_limiter": kw.get("rate_limiter", _lim)})
sys.path.insert(0, "src"); runpy.run_path("src/evaluate.py", run_name="__main__")
```

---

## Técnicas Aplicadas (Fase 2)

O prompt otimizado (`prompts/bug_to_user_story_v2.yml`) combina **três técnicas**
(declaradas em `techniques_applied`):

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
métricas (e, por consequência, as derivadas Helpfulness e Correctness).

> O `user_prompt` é exatamente `"{bug_report}"` — a única variável de template; todo o
> conhecimento (persona, regras, exemplos) vive no `system_prompt`.

---

## Resultados Finais

Avaliação real (`python src/evaluate.py`, 15/15 exemplos, modelo `gemini-3.1-flash-lite`
com throttle de 14 RPM), puxando o v2 do Hub:

```
==================================================
Prompt: rodrigorjsf/bug_to_user_story_v2
==================================================

Métricas Derivadas:
- Helpfulness: 0.81 ✓
- Correctness: 0.84 ✓

Métricas Base:
- F1-Score: 0.88 ✓
- Clarity: 0.81 ✓
- Precision: 0.80 ✓

📊 MÉDIA GERAL: 0.8277
✅ STATUS: APROVADO - Todas as métricas >= 0.8
```

### Tabela comparativa v1 vs v2

| Métrica | v1 (baseline) | v2 (otimizado) | Limiar |
|---|---|---|---|
| Helpfulness | 0.45 ✗ | **0.81** ✓ | 0.80 |
| Correctness | 0.52 ✗ | **0.84** ✓ | 0.80 |
| F1-Score | 0.48 ✗ | **0.88** ✓ | 0.80 |
| Clarity | 0.50 ✗ | **0.81** ✓ | 0.80 |
| Precision | 0.46 ✗ | **0.80** ✓ | 0.80 |
| **Média** | **~0.48** ✗ | **0.8277** ✓ | 0.80 |

> A coluna **v1** corresponde ao ponto de partida de baixa qualidade
> (`leonanluppi/bug_to_user_story_v1`) — números ilustrativos conforme o enunciado do
> desafio. A coluna **v2** é a medição real do prompt otimizado deste repositório.

### Evidências no LangSmith

- **Projeto / dashboard:** <https://smith.langchain.com/projects/MBA-evaluation-prompt>
- **Prompt v2 público:** <https://smith.langchain.com/prompts/bug_to_user_story_v2>
- **Dataset** `MBA-evaluation-prompt-eval` com os 15 exemplos; tracing visível para todos.
- _Screenshots do dashboard com as notas ≥ 0.8: a anexar._

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

Os juízes (LLM-as-Judge, em `src/metrics.py`) produzem 3 métricas-base e 2 derivadas:

| Métrica | Como é calculada |
|---|---|
| **F1-Score** | média harmônica de precision/recall da resposta vs. a referência |
| **Clarity** | organização, linguagem simples, ausência de ambiguidade, concisão |
| **Precision** | ausência de alucinação, foco na pergunta, correção factual |
| **Helpfulness** | derivada: `(Clarity + Precision) / 2` |
| **Correctness** | derivada: `(F1 + Precision) / 2` |

Como **Precision** alimenta as duas derivadas, é a métrica de maior alavancagem.
Aprovação exige **todas as 5 ≥ 0.8** (não apenas a média).

---

## Estrutura do projeto

```
mba-ia-pull-evaluation-prompt/
├── .env.example
├── requirements.txt
├── README.md
├── prompts/
│   ├── bug_to_user_story_v1.yml   # baseline puxado do Hub
│   └── bug_to_user_story_v2.yml   # prompt otimizado (entregável)
├── datasets/
│   └── bug_to_user_story.jsonl    # 15 bugs (5 simples, 7 médios, 3 complexos)
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
