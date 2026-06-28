"""
Unit tests for pull_prompts.py — all network calls are mocked.
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Add src/ to path so pull_prompts is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pull_prompts

PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"
SYSTEM_TEMPLATE = "Você é um assistente que ajuda a transformar relatos de bugs de usuários em tarefas para desenvolvedores."
USER_TEMPLATE = "{bug_report}"


def _make_mock_chat_prompt(system_template: str = SYSTEM_TEMPLATE,
                            user_template: str = USER_TEMPLATE) -> MagicMock:
    """Build a minimal ChatPromptTemplate mock with system and user messages."""
    system_msg = MagicMock()
    system_msg.prompt.template = system_template

    user_msg = MagicMock()
    user_msg.prompt.template = user_template

    mock_prompt = MagicMock()
    mock_prompt.messages = [system_msg, user_msg]
    return mock_prompt


class TestPullPromptsFromLangsmith:
    """Tests for pull_prompts_from_langsmith()."""

    def test_hub_pull_called_with_v1_name(self):
        """hub.pull must be invoked with the exact v1 prompt name."""
        mock_prompt = _make_mock_chat_prompt()

        with patch.object(pull_prompts.hub, "pull", return_value=mock_prompt) as mock_pull, \
             patch("pull_prompts.save_yaml", return_value=True), \
             patch("pull_prompts.check_env_vars", return_value=True):

            pull_prompts.pull_prompts_from_langsmith()

            mock_pull.assert_called_once_with(PROMPT_NAME)

    def test_save_yaml_called_with_system_and_user_prompt(self):
        """save_yaml must receive a dict containing system_prompt and user_prompt."""
        mock_prompt = _make_mock_chat_prompt()

        with patch.object(pull_prompts.hub, "pull", return_value=mock_prompt), \
             patch("pull_prompts.save_yaml", return_value=True) as mock_save, \
             patch("pull_prompts.check_env_vars", return_value=True):

            pull_prompts.pull_prompts_from_langsmith()

            assert mock_save.called, "save_yaml was not called"
            saved_data, _path = mock_save.call_args[0]

            # The data can be wrapped under the prompt key or flat — check recursively
            all_keys = set(saved_data.keys())
            nested = next(iter(saved_data.values())) if len(all_keys) == 1 else saved_data
            if isinstance(nested, dict):
                data_to_check = nested
            else:
                data_to_check = saved_data

            assert "system_prompt" in data_to_check, (
                f"Expected 'system_prompt' in saved data. Got keys: {list(data_to_check.keys())}"
            )
            assert "user_prompt" in data_to_check, (
                f"Expected 'user_prompt' in saved data. Got keys: {list(data_to_check.keys())}"
            )

    def test_save_yaml_receives_correct_template_content(self):
        """save_yaml must persist the exact template strings extracted from hub."""
        mock_prompt = _make_mock_chat_prompt(
            system_template=SYSTEM_TEMPLATE,
            user_template=USER_TEMPLATE,
        )

        with patch.object(pull_prompts.hub, "pull", return_value=mock_prompt), \
             patch("pull_prompts.save_yaml", return_value=True) as mock_save, \
             patch("pull_prompts.check_env_vars", return_value=True):

            pull_prompts.pull_prompts_from_langsmith()

            saved_data, _path = mock_save.call_args[0]
            nested = next(iter(saved_data.values())) if len(saved_data) == 1 else saved_data
            data = nested if isinstance(nested, dict) else saved_data

            assert data["system_prompt"] == SYSTEM_TEMPLATE
            assert data["user_prompt"] == USER_TEMPLATE

    def test_missing_credentials_returns_false(self):
        """When LANGSMITH_API_KEY is absent, function must return False (non-zero exit)."""
        with patch("pull_prompts.check_env_vars", return_value=False) as mock_check, \
             patch.object(pull_prompts.hub, "pull") as mock_pull:

            result = pull_prompts.pull_prompts_from_langsmith()

            assert result is False, "Expected False when credentials are missing"
            mock_pull.assert_not_called()

    def test_hub_not_found_returns_false(self, capsys):
        """When hub.pull raises an exception, function must return False."""
        with patch("pull_prompts.check_env_vars", return_value=True), \
             patch.object(pull_prompts.hub, "pull", side_effect=Exception("404 Not Found")):

            result = pull_prompts.pull_prompts_from_langsmith()

            assert result is False, "Expected False when prompt is not found"
            captured = capsys.readouterr()
            assert captured.out, "Expected an actionable message printed to stdout"


class TestMain:
    """Smoke tests for main()."""

    def test_main_exits_nonzero_on_missing_env(self):
        """main() must exit with a non-zero code when credentials are absent."""
        with patch("pull_prompts.pull_prompts_from_langsmith", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                pull_prompts.main()
            assert exc_info.value.code != 0

    def test_main_exits_zero_on_success(self):
        """main() must exit 0 (or return 0) when pull succeeds."""
        with patch("pull_prompts.pull_prompts_from_langsmith", return_value=True):
            result = pull_prompts.main()
            # main() should return 0 (or None) on success
            assert result in (0, None)
