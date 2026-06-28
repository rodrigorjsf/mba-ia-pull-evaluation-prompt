"""
evaluate_throttled.py — executa o `src/evaluate.py` ORIGINAL sob um limitador de taxa.

Por que existe
--------------
`src/evaluate.py` é imutável (exigência do SPEC) e não possui throttling embutido. No free
tier do Gemini, o modelo `gemini-3.1-flash-lite` retorna `429` quando o `evaluate.py` dispara
seu burst de ~60 chamadas por execução (15 gerações + 45 juízes). Pior: nesse caso o
`evaluate.py` descarta o exemplo silenciosamente (resposta vazia → pulada), corrompendo as
notas.

O que faz
---------
Injeta um `InMemoryRateLimiter` (~14 RPM, abaixo do limite de 15 RPM) em TODA instância de
`ChatGoogleGenerativeAI` — gerador e juízes compartilham o mesmo balde — SEM tocar em nenhum
arquivo de `src/`. Em seguida executa o `src/evaluate.py` original via `runpy`.

A lógica de avaliação é EXATAMENTE a mesma do `evaluate.py` original; apenas o ritmo das
chamadas à API muda. Nenhuma métrica, prompt ou regra de aprovação é alterada aqui.

Uso
---
    python evaluate_throttled.py
"""

import os
import runpy
import sys
from pathlib import Path

import langchain_google_genai as lcg
from langchain_core.rate_limiters import InMemoryRateLimiter


def install_rate_limiter(rpm: int = 14) -> InMemoryRateLimiter:
    """Faz monkeypatch em ChatGoogleGenerativeAI para que toda instância compartilhe um
    único limitador de ~rpm/min. Retorna o limitador (útil para testes)."""
    limiter = InMemoryRateLimiter(
        requests_per_second=rpm / 60,
        check_every_n_seconds=0.5,
        max_bucket_size=1,
    )
    original_init = lcg.ChatGoogleGenerativeAI.__init__

    def init_with_limiter(self, **kwargs):
        kwargs.setdefault("rate_limiter", limiter)
        original_init(self, **kwargs)

    lcg.ChatGoogleGenerativeAI.__init__ = init_with_limiter
    return limiter


if __name__ == "__main__":
    install_rate_limiter(14)

    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    os.chdir(repo_root)            # evaluate.py usa caminhos relativos (datasets/, prompts/)
    sys.path.insert(0, str(src_dir))

    # Executa o evaluate.py imutável como se fosse `python src/evaluate.py`.
    runpy.run_path(str(src_dir / "evaluate.py"), run_name="__main__")
