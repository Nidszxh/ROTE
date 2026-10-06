from __future__ import annotations

from pathlib import Path

from src.evaluation import evaluate
from src.loader.loader import load_day


def generate_evaluation_report(
    stocks: list[str],
    days: list[int],
    theta: list[float],
    out_path: Path = Path("results/EVALUATION_REPORT.md"),
) -> Path:
    """Run the configured comparison and write a compact Markdown table."""
    books = {}
    windows = {}
    for stock in stocks:
        for day in days:
            book, _, _ = load_day(stock, day)
            key = f"{stock}-day{day}"
            books[key] = book
            end = len(book["M"])
            windows[key] = [slice(100, end), slice(100, max(100, end // 2))]
    result = evaluate(books, windows, theta=theta)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ROTE evaluation",
        "",
        "## Strategy summary",
        "",
        "| Strategy | θ | Metric | Mean | 95% CI | n |",
        "| --- | ---: | --- | ---: | --- | ---: |",
    ]
    for row in result.summary.itertuples(index=False):
        lines.append(
            f"| {row.strategy} | {row.theta:g} | {row.metric} | "
            f"{row.mean:.4f} | [{row.ci_low:.4f}, {row.ci_high:.4f}] | {row.n} |"
        )
    if not result.comparisons.empty:
        lines.extend(
            [
                "",
                "## Holm-corrected paired comparisons",
                "",
                "| Comparison | Difference | p | Holm p | Reject |",
                "| --- | ---: | ---: | ---: | --- |",
            ]
        )
        for row in result.comparisons.itertuples(index=False):
            lines.append(
                f"| {row.comparison} | {row.mean_difference:.4f} | "
                f"{row.p_value:.4f} | {row.p_adjusted:.4f} | {row.reject} |"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
