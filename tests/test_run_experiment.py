"""
Unit tests for run_experiment.py — fully offline (no network).

Locks the load-bearing logic of the v2 LangSmith Experiment runner:

1. The metric -> evaluator adapter: a SINGLE combined evaluator calls each of
   the three immutable Base Metrics (`evaluate_f1_score`, `evaluate_clarity`,
   `evaluate_precision`) EXACTLY ONCE and surfaces five per-example feedback
   keys.
2. The Derived Metric math: helpfulness = (clarity + precision) / 2 and
   correctness = (f1 + precision) / 2.

The three base scorers are stubbed, so no LLM/judge call is made. A socket
guard proves the adapter performs zero network I/O.
"""
import socket
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Root scripts import src modules by bare name; mirror evaluate_throttled.py /
# the other root-script tests by injecting both repo root and src/ on sys.path.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "src"))

import run_experiment


def _fake_run(answer: str) -> MagicMock:
    """A LangSmith Run whose target output dict carries the generated answer."""
    run = MagicMock()
    run.outputs = {"answer": answer}
    return run


def _fake_example(bug_report: str, reference: str) -> MagicMock:
    """A LangSmith Example: inputs hold the bug report, outputs hold the reference."""
    example = MagicMock()
    example.inputs = {"bug_report": bug_report}
    example.outputs = {"reference": reference}
    return example


def _run_combined_evaluator():
    """Invoke the combined evaluator with the three base scorers stubbed."""
    with patch(
        "run_experiment.evaluate_f1_score", return_value={"score": 0.8, "reasoning": "x"}
    ) as m_f1, patch(
        "run_experiment.evaluate_clarity", return_value={"score": 0.9, "reasoning": "x"}
    ) as m_clarity, patch(
        "run_experiment.evaluate_precision", return_value={"score": 0.7, "reasoning": "x"}
    ) as m_precision:
        run = _fake_run("generated user story")
        example = _fake_example("login button broken", "expected reference story")
        result = run_experiment.combined_evaluator(run, example)
    return result, m_f1, m_clarity, m_precision


def test_combined_evaluator_returns_five_feedback_keys():
    """All five metrics surface as per-example feedback in one pass."""
    result, _, _, _ = _run_combined_evaluator()

    assert "results" in result
    keys = {r["key"] for r in result["results"]}
    assert keys == {"f1_score", "clarity", "precision", "helpfulness", "correctness"}


def test_combined_evaluator_derived_metric_math():
    """helpfulness = (clarity+precision)/2 ; correctness = (f1+precision)/2."""
    result, _, _, _ = _run_combined_evaluator()
    scores = {r["key"]: r["score"] for r in result["results"]}

    # Base metrics pass through unchanged.
    assert scores["f1_score"] == pytest.approx(0.8)
    assert scores["clarity"] == pytest.approx(0.9)
    assert scores["precision"] == pytest.approx(0.7)

    # Derived metrics computed from the base scores.
    assert scores["helpfulness"] == pytest.approx((0.9 + 0.7) / 2)  # 0.8
    assert scores["correctness"] == pytest.approx((0.8 + 0.7) / 2)  # 0.75


def test_each_base_scorer_called_exactly_once():
    """Precision must not be recomputed: each base scorer fires exactly once."""
    _, m_f1, m_clarity, m_precision = _run_combined_evaluator()

    m_f1.assert_called_once()
    m_clarity.assert_called_once()
    m_precision.assert_called_once()


def test_base_scorers_receive_question_answer_reference():
    """Adapter wires bug_report->question, run answer->answer, example->reference."""
    with patch(
        "run_experiment.evaluate_f1_score", return_value={"score": 0.8}
    ) as m_f1, patch(
        "run_experiment.evaluate_clarity", return_value={"score": 0.9}
    ), patch(
        "run_experiment.evaluate_precision", return_value={"score": 0.7}
    ):
        run = _fake_run("the answer")
        example = _fake_example("the bug report", "the reference")
        run_experiment.combined_evaluator(run, example)

    # Base metric signature is (question, answer, reference).
    args, kwargs = m_f1.call_args
    passed = list(args) + list(kwargs.values())
    assert "the bug report" in passed  # question
    assert "the answer" in passed      # answer
    assert "the reference" in passed   # reference


def test_combined_evaluator_does_no_network(monkeypatch):
    """The adapter itself must perform zero network I/O (base scorers stubbed)."""

    def _no_network(*_args, **_kwargs):
        raise AssertionError("network access attempted inside combined_evaluator")

    monkeypatch.setattr(socket, "socket", _no_network)

    with patch("run_experiment.evaluate_f1_score", return_value={"score": 0.5}), \
         patch("run_experiment.evaluate_clarity", return_value={"score": 0.5}), \
         patch("run_experiment.evaluate_precision", return_value={"score": 0.5}):
        result = run_experiment.combined_evaluator(
            _fake_run("a"), _fake_example("b", "c")
        )

    assert {r["key"] for r in result["results"]} == {
        "f1_score",
        "clarity",
        "precision",
        "helpfulness",
        "correctness",
    }


def test_combined_evaluator_reads_score_defensively():
    """A base scorer dict missing 'score' degrades to 0.0 rather than raising."""
    with patch("run_experiment.evaluate_f1_score", return_value={"reasoning": "no score"}), \
         patch("run_experiment.evaluate_clarity", return_value={"score": 0.6}), \
         patch("run_experiment.evaluate_precision", return_value={"score": 0.4}):
        result = run_experiment.combined_evaluator(
            _fake_run("a"), _fake_example("b", "c")
        )

    scores = {r["key"]: r["score"] for r in result["results"]}
    assert scores["f1_score"] == pytest.approx(0.0)
    assert scores["correctness"] == pytest.approx((0.0 + 0.4) / 2)


# --- version selection (the additive v0/v2 runner switch) -------------------

def test_pull_prompt_builds_versioned_hub_name():
    """pull_prompt forms `<handle>/bug_to_user_story_<version>` and never the
    network at import — the hub call is patched."""
    with patch("run_experiment.hub.pull", return_value=MagicMock()) as mock_pull:
        run_experiment.pull_prompt("rodrigorjsf", "v0")
    mock_pull.assert_called_once_with("rodrigorjsf/bug_to_user_story_v0")


def test_main_routes_version_to_create_experiment():
    """main(version=...) forwards the selected version to create_experiment."""
    for version in ("v0", "v2"):
        with patch("run_experiment.create_experiment", return_value=0) as mock_ce:
            rc = run_experiment.main(version=version)
        assert rc == 0
        mock_ce.assert_called_once_with(version)


def test_main_defaults_to_v2_when_no_arg(monkeypatch):
    """With no CLI arg, main() defaults to v2 (backward-compatible)."""
    monkeypatch.setattr(run_experiment.sys, "argv", ["run_experiment.py"])
    with patch("run_experiment.create_experiment", return_value=0) as mock_ce:
        run_experiment.main()
    mock_ce.assert_called_once_with("v2")


def test_main_rejects_invalid_version():
    """An unknown version is rejected before any experiment is created."""
    with patch("run_experiment.create_experiment") as mock_ce:
        rc = run_experiment.main(version="v9")
    assert rc == 2
    mock_ce.assert_not_called()
