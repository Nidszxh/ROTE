from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.benchmarks.baselines import depth_proportional_plan, twap_plan, vwap_proxy_plan
from src.loader.loader import STOCK_NAMES, load_day
from src.models.m1_ac import solve_m1
from src.models.m2_lp import solve_m2
from src.models.m3_mip import solve_m3
from src.models.m4_ahp import ahp_consistency_ratio, ahp_weights
from src.reports.visualizations import (
    plot_ahp_ranking,
    plot_benchmark_frontier,
    plot_lob_ladder,
    plot_m1_frontier,
    plot_m2_diagnostics,
    plot_m3_tradeoff,
    plot_microstructure_analytics,
)
from src.sim.simulate import simulate
from src.stats.stats import compute_statistics
from src.utils.contracts import Order


def generate_all_reports_and_figures(
    stock: str = STOCK_NAMES[0],
    day: int = 8,
    out_dir: Path | None = None,
) -> Path:
    """
    Run full model suite, generate high-resolution figures, and compile an
    executive Markdown execution report.
    """
    if out_dir is None:
        out_dir = Path("results/figures")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data for {stock} on Day {day} (Held-out Test)...")
    book_raw, _, _ = load_day(stock, day)

    # 1. Microstructure Figures
    print("Generating Figure: LOB Depth Ladder...")
    fig_ladder = plot_lob_ladder(book_raw, snapshot_idx=100)
    fig_ladder.savefig(out_dir / "lob_depth_ladder.png", bbox_inches="tight")

    print("Generating Figure: Microstructure Analytics...")
    fig_micro = plot_microstructure_analytics(book_raw, max_points=300)
    fig_micro.savefig(out_dir / "microstructure_dashboard.png", bbox_inches="tight")

    # Setup execution slice
    Q = 5000.0
    T = 20
    step = 20
    T_rows = T * step
    book = {k: v[:T_rows:step] for k, v in book_raw.items()}
    order = Order(side="buy", size=Q, horizon=T, params={})

    # 2. M1 Frontier
    print("Generating Figure: M1 Efficient Frontier...")
    fig_m1, m1_df = plot_m1_frontier(order, book)
    fig_m1.savefig(out_dir / "m1_efficient_frontier.png", bbox_inches="tight")

    # 3. M2 Diagnostics
    print("Generating Figure: M2 LOB Liquidity Diagnostics...")
    fig_m2 = plot_m2_diagnostics(order, book, rho=0.25)
    fig_m2.savefig(out_dir / "m2_liquidity_diagnostics.png", bbox_inches="tight")

    # 4. M3 Tradeoff
    print("Generating Figure: M3 Fixed-Charge Trade-off...")
    fig_m3 = plot_m3_tradeoff(order, book)
    fig_m3.savefig(out_dir / "m3_fixed_charge_tradeoff.png", bbox_inches="tight")

    # 5. Benchmark Comparison
    print("Generating Figure: Benchmark Multi-Model Comparison...")
    params = {
        "lambda_imp": 0.05,
        "rho": 0.25,
        "eta": 0.1,
        "sigma": 0.015,
        "c_f": 5.0,
        "L_min": 100.0,
    }

    schedules = {
        "M1": solve_m1(order, book, params).shares,
        "M2": solve_m2(order, book, params).shares,
        "M3": solve_m3(order, book, params).shares,
        "TWAP": twap_plan(order).shares,
        "Depth-Prop": depth_proportional_plan(order, book).shares,
        "VWAP Proxy": vwap_proxy_plan(order, book).shares,
    }

    results = []
    for name, sh in schedules.items():
        sched_obj = solve_m1(order, book, params)
        object.__setattr__(sched_obj, "shares", np.asarray(sh, dtype=float))
        rep = simulate(sched_obj, book)
        results.append(
            {
                "Model": name,
                "Shortfall (bps)": rep.shortfall_bps,
                "Risk (std)": rep.std,
                "Trades": rep.trades,
            }
        )

    compare_df = pd.DataFrame(results)
    fig_bench = plot_benchmark_frontier(compare_df, schedules)
    fig_bench.savefig(out_dir / "benchmark_frontier_comparison.png", bbox_inches="tight")

    # 6. AHP Decision Ranking
    print("Generating Figure: AHP Multi-Criteria Decision Ranking...")
    matrix = np.array(
        [
            [1.0, 3.0, 2.0],
            [1 / 3, 1.0, 0.5],
            [0.5, 2.0, 1.0],
        ]
    )
    cr, _ = ahp_consistency_ratio(matrix)
    weights = ahp_weights(matrix)

    scores_df = compare_df.copy()
    scores_df["norm_cost"] = 1.0 / (scores_df["Shortfall (bps)"] + 1e-4)
    scores_df["norm_risk"] = 1.0 / (scores_df["Risk (std)"] + 1e-4)
    scores_df["norm_simp"] = 1.0 / (scores_df["Trades"] + 1e-4)

    for col in ["norm_cost", "norm_risk", "norm_simp"]:
        c_sum = scores_df[col].sum()
        scores_df[col] = scores_df[col] / c_sum if c_sum > 0 else 0.0

    scores_df["Score"] = (
        scores_df["norm_cost"] * weights[0]
        + scores_df["norm_risk"] * weights[1]
        + scores_df["norm_simp"] * weights[2]
    )

    fig_ahp = plot_ahp_ranking(weights, scores_df)
    fig_ahp.savefig(out_dir / "ahp_decision_ranking.png", bbox_inches="tight")

    # 7. Compile Markdown Report
    stats = compute_statistics(book_raw)
    report_path = Path("results/MODEL_EXECUTION_REPORT.md")
    winner = scores_df.sort_values("Score", ascending=False).iloc[0]["Model"]

    lines = [
        "# ROTE: Comprehensive Model Execution & Microstructure Report",
        f"**Asset**: {stock} | **Test Period**: Day {day} | **Size**: {Q:.0f} shares ($T={T}$)",
        "",
        "---",
        "",
        "## 1. Microstructure Environment",
        f"- **Average Half-Spread**: {stats['avg_half_spread_bps']:.2f} bps",
        f"- **Average Ask Depth**: {stats['avg_depth_ask']:.0f} shares",
        f"- **Average Bid Depth**: {stats['avg_depth_bid']:.0f} shares",
        f"- **Order Book Imbalance (Mean)**: {stats['avg_imbalance']:.4f}",
        f"- **Short-Term Volatility**: {stats['volatility_bps_per_period']:.2f} bps/period",
        "",
        "![LOB Depth Ladder](figures/lob_depth_ladder.png)",
        "![Microstructure Dashboard](figures/microstructure_dashboard.png)",
        "",
        "---",
        "",
        "## 2. Multi-Model Benchmark Comparison Table",
        "",
        "| Model | Implementation Shortfall (bps) | Timing Risk (Std Dev) | Active Trades |",
        "| :--- | :---: | :---: | :---: |",
    ]

    for _, r in compare_df.iterrows():
        lines.append(
            f"| **{r['Model']}** | {r['Shortfall (bps)']:.2f} | "
            f"{r['Risk (std)']:.2f} | {r['Trades']} |"
        )

    lines.extend(
        [
            "",
            "![Benchmark Frontier Comparison](figures/benchmark_frontier_comparison.png)",
            "",
            "---",
            "",
            "## 3. Mathematical Optimization Deep Dive",
            "",
            "### M1: Almgren-Chriss Mean-Variance Efficient Frontier",
            "![M1 Efficient Frontier](figures/m1_efficient_frontier.png)",
            "- As risk aversion lambda increases, execution front-loads to curb volatility risk.",
            "",
            "### M2: Limit Order Book LP with Shadow Prices",
            "![M2 Liquidity Diagnostics](figures/m2_liquidity_diagnostics.png)",
            "- Shadow prices identify binding depth constraints where liquidity bottlenecks occur.",
            "",
            "### M3: Fixed-Charge Mixed-Integer Program",
            "![M3 Tradeoff](figures/m3_fixed_charge_tradeoff.png)",
            "- Fixed fees enforce child order sparsity, reducing ticket fee overhead.",
            "",
            "---",
            "",
            "## 4. Multi-Criteria Strategy Selection (AHP)",
            f"- **Consistency Ratio (CR)**: {cr:.4f} (Valid: $CR < 0.10$)",
            f"- **Weights**: Cost={weights[0] * 100:.1f}%, Risk={weights[1] * 100:.1f}%, "
            f"Simplicity={weights[2] * 100:.1f}%",
            f"- **Recommended Strategy**: **{winner}**",
            "",
            "![AHP Decision Ranking](figures/ahp_decision_ranking.png)",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report successfully compiled to {report_path}")
    return report_path


if __name__ == "__main__":
    generate_all_reports_and_figures()
