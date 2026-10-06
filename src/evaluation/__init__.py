"""Evaluation utilities for comparing execution strategies."""

from src.evaluation.core import (
    EvaluationResult,
    bootstrap_mean_ci,
    evaluate,
    holm_correction,
    run_evaluation,
)

__all__ = [
    "EvaluationResult",
    "bootstrap_mean_ci",
    "evaluate",
    "holm_correction",
    "run_evaluation",
]
