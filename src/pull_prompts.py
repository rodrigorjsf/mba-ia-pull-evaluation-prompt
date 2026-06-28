"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = str(Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v1.yml")

REQUIRED_ENV_VARS = ["LANGSMITH_API_KEY"]


def pull_prompts_from_langsmith():
    """
    Pull the v1 prompt from LangSmith Hub and persist it locally.

    Returns:
        True on success, False on any failure (missing credentials, not found, etc.)
    """
    print_section_header("Pulling prompts from LangSmith Hub")

    if not check_env_vars(REQUIRED_ENV_VARS):
        print(
            "\nActionable fix: create a .env file based on .env.example and set "
            "LANGSMITH_API_KEY to your LangSmith API key.\n"
            "Get one at: https://smith.langchain.com/settings"
        )
        return False

    print(f"Pulling: {PROMPT_NAME} ...")
    try:
        prompt = hub.pull(PROMPT_NAME)
    except Exception as exc:
        print(
            f"\n❌ Failed to pull '{PROMPT_NAME}' from LangSmith Hub.\n"
            f"   Error: {exc}\n"
            f"   Check that the prompt name is correct and your LANGSMITH_API_KEY is valid.\n"
            f"   Hub URL: https://smith.langchain.com/hub/{PROMPT_NAME}"
        )
        return False

    messages = prompt.messages
    system_template = messages[0].prompt.template
    user_template = messages[1].prompt.template

    data = {
        "bug_to_user_story_v1": {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": system_template,
            "user_prompt": user_template,
            "version": "v1",
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }

    success = save_yaml(data, OUTPUT_PATH)
    if success:
        print(f"✅ Prompt saved to: {OUTPUT_PATH}")
    else:
        print(f"❌ Failed to save prompt to: {OUTPUT_PATH}")
        return False

    return True


def main():
    """Função principal"""
    success = pull_prompts_from_langsmith()
    if not success:
        sys.exit(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
