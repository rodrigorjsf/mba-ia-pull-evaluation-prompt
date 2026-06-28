"""
Unit tests for push_prompts.py — all network calls are mocked.
"""
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, call

# Add src/ to path so push_prompts is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import push_prompts

HANDLE = "test_user"
PUSH_NAME = f"{HANDLE}/bug_to_user_story_v2"

VALID_PROMPT_DATA = {
    "description": "Test prompt description",
    "system_prompt": "You are a helpful assistant.",
    "user_prompt": "{bug_report}",
    "version": "v2",
    "techniques_applied": ["Few-shot Learning", "Role Prompting"],
    "tags": ["bug-analysis", "user-story"],
}

MALFORMED_PROMPT_DATA_MISSING_FIELD = {
    "system_prompt": "You are a helpful assistant.",
    "version": "v2",
    "techniques_applied": ["Few-shot Learning", "Role Prompting"],
    # missing 'description'
}

MALFORMED_PROMPT_DATA_TODO = {
    "description": "Test",
    "system_prompt": "You are [TODO] assistant.",
    "version": "v2",
    "techniques_applied": ["Few-shot Learning", "Role Prompting"],
}

MALFORMED_PROMPT_DATA_FEW_TECHNIQUES = {
    "description": "Test",
    "system_prompt": "You are a helpful assistant.",
    "version": "v2",
    "techniques_applied": ["Only one technique"],
}


class TestValidatePrompt:
    """Tests for validate_prompt()."""

    def test_valid_prompt_returns_true(self):
        """A prompt with all required fields and >= 2 techniques is valid."""
        is_valid, errors = push_prompts.validate_prompt(VALID_PROMPT_DATA)
        assert is_valid is True
        assert errors == []

    def test_missing_required_field_returns_false(self):
        """A prompt missing a required field is invalid."""
        is_valid, errors = push_prompts.validate_prompt(MALFORMED_PROMPT_DATA_MISSING_FIELD)
        assert is_valid is False
        assert len(errors) > 0

    def test_todo_in_system_prompt_returns_false(self):
        """A prompt with [TODO] in system_prompt is invalid."""
        is_valid, errors = push_prompts.validate_prompt(MALFORMED_PROMPT_DATA_TODO)
        assert is_valid is False
        assert any("TODO" in e for e in errors)

    def test_fewer_than_two_techniques_returns_false(self):
        """A prompt with fewer than 2 techniques is invalid."""
        is_valid, errors = push_prompts.validate_prompt(MALFORMED_PROMPT_DATA_FEW_TECHNIQUES)
        assert is_valid is False
        assert len(errors) > 0


class TestPushPromptToLangsmith:
    """Tests for push_prompt_to_langsmith()."""

    def test_hub_push_called_with_correct_name_and_public_flag(self):
        """hub.push must be called with the v2 name and new_repo_is_public=True."""
        with patch.object(push_prompts.hub, "push", return_value="commit-hash") as mock_push, \
             patch("push_prompts.check_env_vars", return_value=True), \
             patch.dict("os.environ", {"USERNAME_LANGSMITH_HUB": HANDLE}):

            result = push_prompts.push_prompt_to_langsmith(PUSH_NAME, VALID_PROMPT_DATA)

            assert result is True
            mock_push.assert_called_once()
            call_kwargs = mock_push.call_args
            # First positional arg is the repo name
            assert call_kwargs.args[0] == PUSH_NAME
            # The public flag must be set
            assert call_kwargs.kwargs.get("new_repo_is_public") is True

    def test_hub_push_receives_chat_prompt_template(self):
        """hub.push must receive a ChatPromptTemplate built from system and user messages."""
        from langchain_core.prompts import ChatPromptTemplate

        with patch.object(push_prompts.hub, "push", return_value="commit-hash") as mock_push, \
             patch("push_prompts.check_env_vars", return_value=True), \
             patch.dict("os.environ", {"USERNAME_LANGSMITH_HUB": HANDLE}):

            push_prompts.push_prompt_to_langsmith(PUSH_NAME, VALID_PROMPT_DATA)

            call_kwargs = mock_push.call_args
            prompt_arg = call_kwargs.args[1]
            assert isinstance(prompt_arg, ChatPromptTemplate), (
                f"Expected ChatPromptTemplate, got {type(prompt_arg)}"
            )

    def test_malformed_prompt_hub_not_called(self):
        """When prompt is malformed, hub.push must NOT be called and function returns False."""
        with patch.object(push_prompts.hub, "push") as mock_push, \
             patch("push_prompts.check_env_vars", return_value=True), \
             patch.dict("os.environ", {"USERNAME_LANGSMITH_HUB": HANDLE}):

            result = push_prompts.push_prompt_to_langsmith(PUSH_NAME, MALFORMED_PROMPT_DATA_MISSING_FIELD)

            assert result is False
            mock_push.assert_not_called()

    def test_missing_credentials_returns_false(self):
        """When required env vars are missing, function must return False."""
        with patch("push_prompts.check_env_vars", return_value=False), \
             patch.object(push_prompts.hub, "push") as mock_push:

            result = push_prompts.push_prompt_to_langsmith(PUSH_NAME, VALID_PROMPT_DATA)

            assert result is False
            mock_push.assert_not_called()

    def test_hub_push_exception_returns_false(self, capsys):
        """When hub.push raises an exception, function must return False."""
        with patch.object(push_prompts.hub, "push", side_effect=Exception("Network error")), \
             patch("push_prompts.check_env_vars", return_value=True), \
             patch.dict("os.environ", {"USERNAME_LANGSMITH_HUB": HANDLE}):

            result = push_prompts.push_prompt_to_langsmith(PUSH_NAME, VALID_PROMPT_DATA)

            assert result is False
            captured = capsys.readouterr()
            assert captured.out, "Expected an error message printed to stdout"

    def test_push_includes_metadata(self):
        """hub.push should include description and tags metadata."""
        with patch.object(push_prompts.hub, "push", return_value="commit-hash") as mock_push, \
             patch("push_prompts.check_env_vars", return_value=True), \
             patch.dict("os.environ", {"USERNAME_LANGSMITH_HUB": HANDLE}):

            push_prompts.push_prompt_to_langsmith(PUSH_NAME, VALID_PROMPT_DATA)

            call_kwargs = mock_push.call_args
            # Should have some description or tags metadata
            has_description = "new_repo_description" in call_kwargs.kwargs
            has_tags = "tags" in call_kwargs.kwargs
            assert has_description or has_tags, (
                "hub.push should include new_repo_description or tags metadata"
            )


class TestMain:
    """Smoke tests for main()."""

    def test_main_exits_nonzero_on_missing_env(self):
        """main() must exit with non-zero when credentials are absent."""
        with patch("push_prompts.push_prompt_to_langsmith", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                push_prompts.main(version="v2")
            assert exc_info.value.code != 0

    def test_main_exits_zero_on_success(self):
        """main() must exit 0 (or return 0) when push succeeds."""
        with patch("push_prompts.push_prompt_to_langsmith", return_value=True):
            result = push_prompts.main(version="v2")
            assert result in (0, None)


class TestMainVersionSelection:
    """Smoke tests for version-selection in main() — no network calls."""

    def test_main_v0_calls_push_with_v0_name(self):
        """main(version='v0') must call push_prompt_to_langsmith with a name ending in /bug_to_user_story_v0."""
        with patch("push_prompts.push_prompt_to_langsmith", return_value=True) as mock_push, \
             patch.dict("os.environ", {"USERNAME_LANGSMITH_HUB": HANDLE}):
            result = push_prompts.main(version="v0")
            assert result in (0, None)
            mock_push.assert_called_once()
            prompt_name = mock_push.call_args.args[0]
            assert prompt_name.endswith("/bug_to_user_story_v0"), (
                f"Expected name ending in /bug_to_user_story_v0, got: {prompt_name}"
            )

    def test_main_v2_calls_push_with_v2_name(self):
        """main(version='v2') must call push_prompt_to_langsmith with a name ending in /bug_to_user_story_v2."""
        with patch("push_prompts.push_prompt_to_langsmith", return_value=True) as mock_push, \
             patch.dict("os.environ", {"USERNAME_LANGSMITH_HUB": HANDLE}):
            result = push_prompts.main(version="v2")
            assert result in (0, None)
            mock_push.assert_called_once()
            prompt_name = mock_push.call_args.args[0]
            assert prompt_name.endswith("/bug_to_user_story_v2"), (
                f"Expected name ending in /bug_to_user_story_v2, got: {prompt_name}"
            )

    def test_main_default_pushes_v2_when_no_argv(self):
        """main() with no explicit version and clean sys.argv must default to v2."""
        with patch("push_prompts.push_prompt_to_langsmith", return_value=True) as mock_push, \
             patch.dict("os.environ", {"USERNAME_LANGSMITH_HUB": HANDLE}), \
             patch.object(sys, "argv", ["push_prompts.py"]):
            result = push_prompts.main()
            assert result in (0, None)
            prompt_name = mock_push.call_args.args[0]
            assert prompt_name.endswith("/bug_to_user_story_v2")

    def test_main_invalid_version_exits_nonzero(self):
        """main(version='bad') must exit with non-zero code and not call hub."""
        with patch("push_prompts.push_prompt_to_langsmith") as mock_push:
            with pytest.raises(SystemExit) as exc_info:
                push_prompts.main(version="bad_version")
            assert exc_info.value.code != 0
            mock_push.assert_not_called()

    def test_main_v0_passes_v0_prompt_data_to_push(self):
        """main(version='v0') must load and forward the v0 YAML data (version field == 'v0')."""
        with patch("push_prompts.push_prompt_to_langsmith", return_value=True) as mock_push, \
             patch.dict("os.environ", {"USERNAME_LANGSMITH_HUB": HANDLE}):
            push_prompts.main(version="v0")
            prompt_data = mock_push.call_args.args[1]
            assert prompt_data.get("version") == "v0", (
                f"Expected prompt version 'v0', got: {prompt_data.get('version')}"
            )
