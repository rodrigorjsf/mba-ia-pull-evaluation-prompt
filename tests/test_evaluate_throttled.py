"""
Guarda do wrapper de throttling (evaluate_throttled.py).

Trava o comportamento crítico: `install_rate_limiter` injeta um único
`InMemoryRateLimiter` (~14 RPM) em TODA instância de `ChatGoogleGenerativeAI`
— gerador e juízes compartilham o mesmo balde — sem nenhuma chamada de rede.
Se um upgrade do LangChain renomear o parâmetro ou a injeção quebrar, este teste falha.
"""
import sys
from pathlib import Path

import langchain_google_genai as lcg
from langchain_core.rate_limiters import InMemoryRateLimiter

# Raiz do repo no path, para importar o script de nível raiz.
sys.path.insert(0, str(Path(__file__).parent.parent))
from evaluate_throttled import install_rate_limiter


def test_install_rate_limiter_injects_shared_limiter():
    limiter = install_rate_limiter(rpm=14)

    assert isinstance(limiter, InMemoryRateLimiter)
    assert abs(limiter.requests_per_second - 14 / 60) < 1e-9

    # Toda instância nova recebe o MESMO limiter (gerador + juízes) — zero rede.
    gen = lcg.ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", google_api_key="dummy")
    judge = lcg.ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", google_api_key="dummy")
    assert gen.rate_limiter is limiter
    assert judge.rate_limiter is limiter


def test_explicit_rate_limiter_is_not_overridden():
    install_rate_limiter(rpm=14)
    custom = InMemoryRateLimiter(requests_per_second=1, check_every_n_seconds=0.5, max_bucket_size=1)
    # setdefault: um rate_limiter passado explicitamente deve prevalecer.
    m = lcg.ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite", google_api_key="dummy", rate_limiter=custom
    )
    assert m.rate_limiter is custom
