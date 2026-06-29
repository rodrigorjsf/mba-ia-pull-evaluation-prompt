"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML.

    Suporta tanto o formato flat (campos no topo) quanto o aninhado no estilo v1
    (todos os campos sob uma única chave-raiz, ex.: ``bug_to_user_story_v2:``).
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict) and len(data) == 1:
        inner = next(iter(data.values()))
        if isinstance(inner, dict) and "system_prompt" in inner:
            return inner
    return data

PROMPT_PATH = str(Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml")

class TestPrompts:
    def test_prompt_has_system_prompt(self):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        data = load_prompts(PROMPT_PATH)
        assert "system_prompt" in data, "Campo 'system_prompt' deve existir no YAML"
        assert data["system_prompt"].strip(), "Campo 'system_prompt' não deve estar vazio"

    def test_prompt_has_role_definition(self):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        data = load_prompts(PROMPT_PATH)
        system_prompt = data.get("system_prompt", "")
        assert "Você é" in system_prompt, (
            "system_prompt deve definir uma persona com 'Você é'"
        )

    def test_prompt_mentions_format(self):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        data = load_prompts(PROMPT_PATH)
        system_prompt = data.get("system_prompt", "")
        format_keywords = ["Como um", "Critérios de Aceitação", "User Story", "Markdown"]
        assert any(kw in system_prompt for kw in format_keywords), (
            "system_prompt deve mencionar o formato esperado (User Story / Markdown): "
            + str(format_keywords)
        )

    def test_prompt_has_few_shot_examples(self):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        data = load_prompts(PROMPT_PATH)
        system_prompt = data.get("system_prompt", "")
        example_keywords = ["Exemplo", "exemplo", "Input:", "Output:", "Bug:", "---"]
        assert any(kw in system_prompt for kw in example_keywords), (
            "system_prompt deve conter exemplos few-shot de entrada/saída"
        )

    def test_prompt_no_todos(self):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        data = load_prompts(PROMPT_PATH)
        system_prompt = data.get("system_prompt", "")
        assert "TODO" not in system_prompt, (
            "system_prompt não deve conter marcadores TODO ou [TODO]"
        )

    def test_minimum_techniques(self):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        data = load_prompts(PROMPT_PATH)
        techniques = data.get("techniques_applied", [])
        assert len(techniques) >= 2, (
            f"Deve haver pelo menos 2 técnicas aplicadas, encontradas: {len(techniques)}"
        )

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
