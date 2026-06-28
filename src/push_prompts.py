"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts de prompts/bug_to_user_story_{version}.yml (v0 ou v2)
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
REQUIRED_ENV_VARS = ["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]
ALLOWED_VERSIONS = {"v0", "v2"}


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    return validate_prompt_structure(prompt_data)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome completo do prompt (handle/name)
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    if not check_env_vars(REQUIRED_ENV_VARS):
        return False

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido — push abortado:")
        for error in errors:
            print(f"   - {error}")
        return False

    system_prompt = prompt_data["system_prompt"]
    user_prompt = prompt_data.get("user_prompt", "{bug_report}")
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_prompt),
    ])

    description = prompt_data.get("description", "")
    techniques = prompt_data.get("techniques_applied", [])
    if techniques:
        description = f"{description} | Techniques: {', '.join(techniques)}"

    tags = prompt_data.get("tags", [])

    try:
        url = hub.push(
            prompt_name,
            chat_prompt,
            new_repo_is_public=True,
            new_repo_description=description,
            tags=tags,
        )
        print(f"✅ Prompt publicado com sucesso: {url}")
        return True
    except Exception as e:
        print(f"❌ Erro ao fazer push para o LangSmith Hub: {e}")
        return False


def main(version=None):
    """Função principal.

    Args:
        version: Versão do prompt a fazer push ('v0' ou 'v2').
                 Quando None, lê de sys.argv[1]; padrão 'v2' se sem argumento.
    """
    print_section_header("Push de Prompt para o LangSmith Hub")

    if version is None:
        version = sys.argv[1] if len(sys.argv) > 1 else "v2"

    if version not in ALLOWED_VERSIONS:
        print(f"❌ Versão inválida: '{version}'. Versões permitidas: {sorted(ALLOWED_VERSIONS)}")
        sys.exit(1)

    handle = os.getenv("USERNAME_LANGSMITH_HUB", "")
    prompt_name = f"{handle}/bug_to_user_story_{version}"
    prompt_file = PROMPTS_DIR / f"bug_to_user_story_{version}.yml"

    prompt_data = load_yaml(str(prompt_file))
    if prompt_data is None:
        print(f"❌ Não foi possível carregar o prompt de {prompt_file}")
        sys.exit(1)

    success = push_prompt_to_langsmith(prompt_name, prompt_data)
    if not success:
        sys.exit(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
