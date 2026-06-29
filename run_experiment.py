"""
run_experiment.py — produz um Experiment NATIVO do LangSmith para o prompt v2.

Por que existe
--------------
`evaluate_throttled.py` roda o `src/evaluate.py` imutável e imprime as notas no
terminal, mas NÃO cria um Experiment pontuado na aba *Experiments* do dashboard
do LangSmith. Este script faz exatamente isso, de forma ADITIVA (não toca em
nada de `src/`):

1. Inventário READ-ONLY do LangSmith (apenas `list_*`, NUNCA `delete_*`).
2. Puxa `<handle>/bug_to_user_story_v2` do Hub — fonte única de verdade
   (não lê o YAML local).
3. Roda `langsmith.evaluation.evaluate()` sobre o dataset já existente
   `<project>-eval` (15 exemplos).
4. Envolve as três Base Metrics imutáveis de `metrics.py`
   (`f1_score`, `clarity`, `precision`) como avaliadores do LangSmith e calcula
   as duas Derived Metrics: `helpfulness=(clarity+precision)/2` e
   `correctness=(f1+precision)/2`.
5. Anexa as cinco como feedback por exemplo (surgem na aba Experiments).
6. Reusa `install_rate_limiter` (Gemini free ~14 RPM) com concorrência BAIXA do
   `evaluate()` (`max_concurrency` 1–2) para não estourar 429.
7. Compartilha o projeto/dataset publicamente.

A matemática das métricas é IDÊNTICA à do `src/evaluate.py` original — apenas a
forma de publicação (Experiment nativo + feedback por exemplo) muda.

Uso
---
    python run_experiment.py [v2]   # padrão: v2

`v2` é o prompt otimizado (APROVA, ≥0.8) — o único prompt que o desafio pede
para avaliar. O runner cria o Experiment pontuado sobre o dataset existente.

Toda I/O de rede acontece DENTRO de `main()`/helpers — nunca no import. Isso
permite importar o módulo (e testar o adaptador de métricas) sem rede.
"""

import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict

# Scripts de nível raiz importam módulos de src/ por nome simples
# (`from metrics import ...`). Espelha evaluate_throttled.py: coloca repo_root e
# src/ no sys.path ANTES dos imports por nome simples.
_REPO_ROOT = Path(__file__).resolve().parent
_SRC_DIR = _REPO_ROOT / "src"
for _p in (str(_SRC_DIR), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from langchain import hub
from langsmith import Client
from langsmith.evaluation import evaluate

from metrics import evaluate_f1_score, evaluate_clarity, evaluate_precision
from utils import check_env_vars, get_llm, print_section_header
from evaluate_throttled import install_rate_limiter


# Concorrência BAIXA: o free tier do Gemini (~14 RPM) estoura 429 com paralelismo
# alto. Mantém entre 1 e 2.
MAX_CONCURRENCY = 1


def _score_of(metric_result: Dict[str, Any]) -> float:
    """Lê `["score"]` defensivamente — as Base Metrics nunca levantam exceção e,
    no pior caso, devolvem `{"score": 0.0}`; mesmo assim protege contra ausência
    da chave ou valor não numérico."""
    try:
        return float(metric_result.get("score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def combined_evaluator(run: Any, example: Any) -> Dict[str, Any]:
    """Avaliador ÚNICO e combinado do LangSmith.

    Chama cada uma das três Base Metrics imutáveis EXATAMENTE UMA VEZ (evita
    recomputar `precision` e dobrar as chamadas de juiz → risco de 429 e
    não-determinismo) e devolve as CINCO métricas como feedback por exemplo:
    as três base (`f1_score`, `clarity`, `precision`) e as duas derivadas
    (`helpfulness`, `correctness`).

    Assinatura `(run, example)`: o LangSmith passa o `Run` (saída do alvo) e o
    `Example` (entrada + referência do dataset). Lê:
      - `answer`    de `run.outputs["answer"]`
      - `question`  de `example.inputs["bug_report"]`
      - `reference` de `example.outputs["reference"]`

    Retorna um `EvaluationResults` no formato dict
    `{"results": [{"key", "score"}, ...]}`, aceito nativamente pelo LangSmith
    para anexar MÚLTIPLAS chaves de feedback em uma só passada.
    """
    run_outputs = getattr(run, "outputs", None) or {}
    answer = run_outputs.get("answer", "")

    example_inputs = getattr(example, "inputs", None) or {}
    question = example_inputs.get(
        "bug_report",
        example_inputs.get("question", example_inputs.get("pr_title", "")),
    )

    reference_outputs = getattr(example, "outputs", None) or {}
    reference = reference_outputs.get("reference", "")

    # Cada Base Metric é chamada UMA única vez.
    f1 = _score_of(evaluate_f1_score(question, answer, reference))
    clarity = _score_of(evaluate_clarity(question, answer, reference))
    precision = _score_of(evaluate_precision(question, answer, reference))

    # Derived Metrics (mesma fórmula do src/evaluate.py imutável).
    helpfulness = (clarity + precision) / 2
    correctness = (f1 + precision) / 2

    # O feedback do LangSmith aceita no máximo 4 casas decimais; as derivadas
    # ((a+b)/2) podem gerar 5+ casas, então arredonda TODAS as cinco para 4 —
    # caso contrário o ingest do feedback falha com HTTP 422 e o score some do
    # dashboard.
    scores = {
        "f1_score": f1,
        "clarity": clarity,
        "precision": precision,
        "helpfulness": helpfulness,
        "correctness": correctness,
    }
    return {"results": [{"key": k, "score": round(v, 4)} for k, v in scores.items()]}


def make_target(prompt_template: Any, llm: Any) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Constrói o alvo do `evaluate()`: roda o prompt v2 contra cada exemplo.

    Espelha `src/evaluate.py:143-168`: `chain = prompt_template | llm;
    answer = chain.invoke(inputs).content`. Devolve `{"answer", "question"}`
    para que `combined_evaluator` leia `run.outputs["answer"]`.
    """
    chain = prompt_template | llm

    def target(inputs: Dict[str, Any]) -> Dict[str, Any]:
        response = chain.invoke(inputs)
        answer = getattr(response, "content", response)
        question = inputs.get(
            "bug_report", inputs.get("question", inputs.get("pr_title", ""))
        )
        return {"answer": answer, "question": question}

    return target


def inventory_langsmith(client: Client) -> None:
    """Inventário READ-ONLY do workspace: apenas `list_*`, NUNCA `delete_*`.

    Lista datasets e projetos existentes para dar visibilidade antes de criar o
    Experiment. Falhas de rede aqui são informativas e não abortam a execução.
    """
    print_section_header("Inventário READ-ONLY do LangSmith", char="-")
    try:
        datasets = list(client.list_datasets())
        print(f"   Datasets encontrados: {len(datasets)}")
        for ds in datasets:
            print(f"     - {ds.name}")
    except Exception as exc:  # pragma: no cover - informativo
        print(f"   ⚠️  Não foi possível listar datasets: {exc}")

    try:
        projects = list(client.list_projects())
        print(f"   Projetos encontrados: {len(projects)}")
    except Exception as exc:  # pragma: no cover - informativo
        print(f"   ⚠️  Não foi possível listar projetos: {exc}")


ALLOWED_VERSIONS = ("v2",)


def pull_prompt(username: str, version: str = "v2") -> Any:
    """Puxa `<handle>/bug_to_user_story_<version>` do Hub (fonte única)."""
    prompt_name = f"{username}/bug_to_user_story_{version}"
    print(f"   Puxando prompt do Hub: {prompt_name}")
    prompt = hub.pull(prompt_name)
    print(f"   ✓ Prompt {version} carregado")
    return prompt


def share_results(client: Client, dataset_name: str) -> None:
    """Compartilha o dataset/Experiment publicamente e imprime o link."""
    try:
        shared = client.share_dataset(dataset_name=dataset_name)
        url = shared.get("url") if isinstance(shared, dict) else None
        if url:
            print(f"\n🔗 Link público (dataset/Experiment): {url}")
        else:
            print(f"\n🔗 Dataset compartilhado: {shared}")
    except Exception as exc:  # pragma: no cover - informativo
        print(f"\n⚠️  Não foi possível compartilhar publicamente: {exc}")


def create_experiment(version: str = "v2") -> int:
    """Cria o Experiment `<version>` pontuado no dashboard do LangSmith."""
    print_section_header(f"EXPERIMENT {version} NATIVO NO LANGSMITH")

    provider = os.getenv("LLM_PROVIDER", "openai")
    required_vars = ["LANGSMITH_API_KEY", "LLM_PROVIDER", "USERNAME_LANGSMITH_HUB"]
    if provider == "openai":
        required_vars.append("OPENAI_API_KEY")
    elif provider in ("google", "gemini"):
        required_vars.append("GOOGLE_API_KEY")

    if not check_env_vars(required_vars):
        return 1

    # Limitador de taxa ANTES de qualquer LLM (alvo ou juízes) ser construído —
    # gerador e juízes compartilham o mesmo balde (~14 RPM).
    install_rate_limiter(14)

    client = Client()

    # 1. Inventário read-only.
    inventory_langsmith(client)

    # 2. Prompt do Hub (fonte única de verdade).
    username = os.getenv("USERNAME_LANGSMITH_HUB", "")
    prompt_template = pull_prompt(username, version)

    # 3. Dataset existente (15 exemplos). Deriva `<project>-eval` por padrão, mas
    # respeita um override explícito `EVAL_DATASET` — o nome do dataset é
    # histórico e pode divergir de LANGSMITH_PROJECT se o projeto foi renomeado.
    project_name = os.getenv("LANGSMITH_PROJECT", "prompt-optimization-challenge-resolved")
    dataset_name = os.getenv("EVAL_DATASET") or f"{project_name}-eval"
    print(f"\n   Dataset de avaliação: {dataset_name}")

    # 4. Alvo + avaliador combinado.
    llm = get_llm(temperature=0)
    target = make_target(prompt_template, llm)

    print("\n   Executando evaluate() (concorrência baixa p/ free tier)...")
    results = evaluate(
        target,
        data=dataset_name,
        evaluators=[combined_evaluator],
        experiment_prefix=f"bug_to_user_story_{version}",
        max_concurrency=MAX_CONCURRENCY,
        metadata={
            "prompt": f"{username}/bug_to_user_story_{version}",
            "provider": provider,
            "llm_model": os.getenv("LLM_MODEL", ""),
            "eval_model": os.getenv("EVAL_MODEL", ""),
        },
        client=client,
    )

    experiment_name = getattr(results, "experiment_name", None)
    if experiment_name:
        print(f"\n✅ Experiment criado: {experiment_name}")

    # 5. Compartilhar publicamente.
    share_results(client, dataset_name)

    print("\n✓ Confira a aba Experiments em: https://smith.langchain.com/")
    return 0


def main(version: str = None) -> int:
    from dotenv import load_dotenv

    load_dotenv()
    if version is None:
        argv = [a for a in sys.argv[1:] if not a.startswith("-")]
        version = argv[0] if argv else "v2"
    if version not in ALLOWED_VERSIONS:
        print(f"❌ Versão inválida: {version!r}. Use uma de {ALLOWED_VERSIONS}.")
        return 2
    return create_experiment(version)


if __name__ == "__main__":
    sys.exit(main())
