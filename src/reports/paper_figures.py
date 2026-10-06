"""Publication-grade figure generation for academic research papers.

Produces high-resolution (300+ DPI), minimalist, clean figures adhering to
top-tier journal styling (Journal of Finance, Review of Financial Studies,
Operations Research, Mathematical Finance).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Curated palette for quantitative finance publications
PALETTE = {
    "m2_lp": "#0D9488",  # Teal (Proposed Queue-Aware LP)
    "rote_static": "#4338CA",  # Indigo (ROTE-Static QP)
    "ac": "#7C3AED",  # Purple (Almgren-Chriss Closed Form)
    "ac_capped": "#A855F7",  # Light Purple (AC with participation cap)
    "twap_T": "#1E3A8A",  # Deep Navy (Full Horizon TWAP)
    "twap_Tprime": "#0284C7",  # Sky Blue (Accelerated TWAP)
    "depth_proportional": "#D97706",  # Amber (Depth Proportional)
    "immediate": "#DC2626",  # Crimson Red (Market Order Sweep)
}

STRATEGY_LABELS = {
    "m2_lp": "M2 (LOB LP)",
    "rote_static": "ROTE-Static (QP)",
    "ac": "Almgren-Chriss",
    "ac_capped": "AC (Capped)",
    "twap_T": "TWAP (Full)",
    "twap_Tprime": "TWAP' (Half)",
    "depth_proportional": "Depth-Prop",
    "immediate": "Immediate (Sweep)",
}


def _apply_paper_theme() -> None:
    """Set publication-grade font, line, and grid aesthetics."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial", "Lucida Grande"],
            "axes.edgecolor": "#94A3B8",
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#F1F5F9",
            "grid.linestyle": "-",
            "grid.linewidth": 0.7,
            "xtick.color": "#334155",
            "ytick.color": "#334155",
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "axes.labelsize": 9.5,
            "axes.titlesize": 10.5,
            "figure.titlesize": 12.0,
            "legend.fontsize": 8.0,
            "legend.framealpha": 0.95,
            "legend.edgecolor": "#E2E8F0",
            "figure.dpi": 300,
            "savefig.dpi": 300,
        }
    )


def parse_evaluation_markdown(md_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse strategy summary and Holm paired comparisons from markdown report."""
    text = md_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]

    summary_rows = []
    comp_rows = []
    section = None

    for line in lines:
        if line.startswith("## Strategy summary"):
            section = "summary"
            continue
        elif line.startswith("## Holm-corrected"):
            section = "comp"
            continue
        elif line.startswith("#"):
            section = None
            continue

        if not line.startswith("|") or "---" in line or "Strategy" in line or "Comparison" in line:
            continue

        parts = [p.strip() for p in line.split("|")[1:-1]]
        if section == "summary" and len(parts) >= 6:
            strat, theta, metric, mean_val, ci_str, n = parts[:6]
            ci_clean = ci_str.strip("[]").split(",")
            ci_low = float(ci_clean[0].strip()) if len(ci_clean) > 0 else float(mean_val)
            ci_high = float(ci_clean[1].strip()) if len(ci_clean) > 1 else float(mean_val)
            summary_rows.append(
                {
                    "strategy": strat,
                    "theta": float(theta),
                    "metric": metric,
                    "mean": float(mean_val),
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "n": int(n),
                }
            )
        elif section == "comp" and len(parts) >= 5:
            comp_name, diff, p_val, holm_p, reject = parts[:5]
            comp_rows.append(
                {
                    "comparison": comp_name,
                    "difference": float(diff),
                    "p_value": float(p_val),
                    "holm_p": float(holm_p),
                    "reject": reject.strip().lower() == "true",
                }
            )

    return pd.DataFrame(summary_rows), pd.DataFrame(comp_rows)


def generate_research_paper_figure(
    summary_df: pd.DataFrame,
    comp_df: pd.DataFrame,
    out_path: Path = Path("results/figures/fig_paper_empirical_results.png"),
) -> Path:
    """
    Generate a 4-panel publication-grade figure synthesizing empirical execution results:
    Panel (a): Empirical Pareto Efficient Frontier (Shortfall vs Risk at theta=1.0)
    Panel (b): Impact Non-Linearity Scaling vs Order Sizing theta in [0.25, 5.0]
    Panel (c): Strategy Cost Ranking with Confidence Intervals
    Panel (d): Forest Plot of Paired Treatment Effects relative to TWAP
    """
    _apply_paper_theme()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11.5, 8.5), dpi=300)

    # -------------------------------------------------------------
    # Panel (a): Pareto Efficient Frontier at theta = 1.0
    # -------------------------------------------------------------
    df_th1 = summary_df[summary_df["theta"] == 1.0]
    p_sf = df_th1[df_th1["metric"] == "shortfall_bps"].set_index("strategy")
    p_rk = df_th1[df_th1["metric"] == "risk"].set_index("strategy")

    strategies_present = [s for s in PALETTE if s in p_sf.index and s in p_rk.index]

    for s in strategies_present:
        cost = p_sf.loc[s, "mean"]
        cost_err = [[cost - p_sf.loc[s, "ci_low"]], [p_sf.loc[s, "ci_high"] - cost]]
        risk = p_rk.loc[s, "mean"]
        risk_err = [[risk - p_rk.loc[s, "ci_low"]], [p_rk.loc[s, "ci_high"] - risk]]
        col = PALETTE.get(s, "#475569")
        label = STRATEGY_LABELS.get(s, s)

        ax1.errorbar(
            risk,
            cost,
            xerr=risk_err,
            yerr=cost_err,
            fmt="o",
            color=col,
            ecolor=col,
            elinewidth=1.2,
            capsize=3.0,
            capthick=1.0,
            markersize=7.0,
            alpha=0.9,
            zorder=4,
        )
        # Position labels cleanly
        dx = 0.08
        dy = 0.35 if s not in ("rote_static", "ac_capped") else -0.7
        ax1.annotate(
            label,
            (risk, cost),
            xytext=(risk + dx, cost + dy),
            fontsize=7.8,
            fontweight="bold" if s == "m2_lp" else "normal",
            color="#0F172A",
            bbox=dict(
                boxstyle="round,pad=0.2", facecolor="white", edgecolor=col, alpha=0.85, lw=0.6
            ),
        )

    # Highlight Pareto dominant boundary
    ax1.set_xlabel(r"Timing Risk Exposure ($\sigma_{\mathrm{IS}}$)")
    ax1.set_ylabel("Implementation Shortfall (basis points)")
    ax1.set_title(
        r"(a) Empirical Risk-Cost Frontier ($\Theta = 1.0$ Confirmatory Size)",
        fontweight="bold",
        loc="left",
    )

    # -------------------------------------------------------------
    # Panel (b): Cost Scaling across Order Sizing Multiplier (theta)
    # -------------------------------------------------------------
    sf_df = summary_df[summary_df["metric"] == "shortfall_bps"]

    key_strategies = [
        "m2_lp",
        "rote_static",
        "twap_T",
        "twap_Tprime",
        "depth_proportional",
        "immediate",
    ]
    markers = ["o", "s", "^", "v", "D", "X"]

    for s, m in zip(key_strategies, markers, strict=False):
        if s not in sf_df["strategy"].values:
            continue
        sub = sf_df[sf_df["strategy"] == s].sort_values("theta")
        col = PALETTE.get(s, "#475569")
        label = STRATEGY_LABELS.get(s, s)
        ax2.plot(
            sub["theta"],
            sub["mean"],
            marker=m,
            color=col,
            lw=1.6,
            markersize=5.0,
            label=label,
        )
        ax2.fill_between(
            sub["theta"],
            sub["ci_low"],
            sub["ci_high"],
            color=col,
            alpha=0.10,
        )

    ax2.axvline(
        1.0, color="#94A3B8", linestyle=":", lw=1.2, label=r"Visible Book Limit ($\theta=1.0$)"
    )
    ax2.set_xlabel(r"Parent Order Size Multiplier $\theta$ ($Q = \theta \bar{D}$)")
    ax2.set_ylabel("Implementation Shortfall (basis points)")
    ax2.set_title(
        "(b) Non-Linear Impact Scaling across Order Size $\theta$", fontweight="bold", loc="left"
    )
    ax2.legend(loc="upper left", frameon=True, fontsize=7.5)

    # -------------------------------------------------------------
    # Panel (c): Strategy Cost Comparison Ranking at theta=1.0
    # -------------------------------------------------------------
    ranking_data = []
    for s in strategies_present:
        row = p_sf.loc[s]
        ranking_data.append(
            {
                "strategy": s,
                "label": STRATEGY_LABELS.get(s, s),
                "mean": row["mean"],
                "ci_low": row["ci_low"],
                "ci_high": row["ci_high"],
                "color": PALETTE.get(s, "#475569"),
            }
        )
    rdf = pd.DataFrame(ranking_data).sort_values("mean", ascending=False)
    y_pos = np.arange(len(rdf))

    bar_colors = [r["color"] for _, r in rdf.iterrows()]
    xerr = [
        rdf["mean"] - rdf["ci_low"],
        rdf["ci_high"] - rdf["mean"],
    ]

    ax3.barh(
        y_pos,
        rdf["mean"],
        xerr=xerr,
        color=bar_colors,
        height=0.55,
        alpha=0.85,
        edgecolor="#334155",
        lw=0.6,
        capsize=3.0,
    )
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(rdf["label"], fontsize=8.5)
    for i, (_, row) in enumerate(rdf.iterrows()):
        ax3.text(
            row["ci_high"] + 0.5,
            i,
            f"{row['mean']:.2f} bps",
            va="center",
            fontsize=8.0,
            fontweight="bold" if row["strategy"] == "m2_lp" else "normal",
            color="#0F172A",
        )

    ax3.set_xlabel("Mean Implementation Shortfall (bps)")
    ax3.set_title(
        r"(c) Ranked Execution Cost at $\Theta=1.0$ ($n=176$ Windows)",
        fontweight="bold",
        loc="left",
    )

    # -------------------------------------------------------------
    # Panel (d): Forest Plot of Treatment Effects relative to TWAP
    # -------------------------------------------------------------
    twap_comps = comp_df[
        comp_df["comparison"].str.contains("twap_T")
        & ~comp_df["comparison"].str.contains("twap_Tprime")
    ].copy()

    if not twap_comps.empty:
        # Standardize so difference is (Strategy - TWAP)
        treat_data = []
        for _, row in twap_comps.iterrows():
            c_name = row["comparison"]
            diff = row["difference"]
            p_adj = row["holm_p"]
            # format is "A - B"
            parts = c_name.split(" - ")
            if len(parts) == 2:
                other = parts[0] if parts[1] == "twap_T" else parts[1]
                sign = 1.0 if parts[1] == "twap_T" else -1.0
                delta = diff * sign
                treat_data.append(
                    {
                        "strategy": other,
                        "label": STRATEGY_LABELS.get(other, other),
                        "delta": delta,
                        "holm_p": p_adj,
                        "color": PALETTE.get(other, "#475569"),
                    }
                )
        tdf = pd.DataFrame(treat_data).sort_values("delta")
        y_tdf = np.arange(len(tdf))

        ax4.axvline(
            0.0, color="#64748B", linestyle="--", lw=1.2, label="TWAP Baseline (Zero Delta)"
        )
        for i, (_, r) in enumerate(tdf.iterrows()):
            sig_star = (
                "***"
                if r["holm_p"] < 0.001
                else ("**" if r["holm_p"] < 0.01 else ("*" if r["holm_p"] < 0.05 else "n.s."))
            )
            ax4.scatter(r["delta"], i, color=r["color"], s=60, zorder=4)
            # Annotate treatment delta
            ax4.text(
                r["delta"] + (0.3 if r["delta"] >= 0 else -0.3),
                i,
                f"{r['delta']:+.2f} bps ({sig_star})",
                va="center",
                ha="left" if r["delta"] >= 0 else "right",
                fontsize=7.8,
                fontweight="bold" if "m2" in r["strategy"] else "normal",
            )
            ax4.hlines(i, 0, r["delta"], color=r["color"], lw=1.5, alpha=0.7)

        ax4.set_yticks(y_tdf)
        ax4.set_yticklabels(tdf["label"], fontsize=8.5)
        ax4.set_xlabel(r"Excess Shortfall vs. TWAP: $\Delta\mathrm{IS}$ (basis points)")
        ax4.set_title(
            r"(d) Holm-Bonferroni Paired Treatment Effects ($*** p < 0.001$)",
            fontweight="bold",
            loc="left",
        )
    else:
        ax4.text(0.5, 0.5, "Comparison data not available", ha="center", va="center")

    fig.suptitle(
        "Empirical Limit Order Book Execution Benchmark on FI-2010\n"
        r"Validation Split (Days 6–7, $N_{\mathrm{eff}}=176$ Independent Windows, $\rho=0.25$)",
        fontsize=12.5,
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path
