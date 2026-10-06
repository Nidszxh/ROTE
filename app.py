"""Streamlit exploration UI for the frozen FI-2010 execution experiment."""

from __future__ import annotations

import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.benchmarks.baselines import depth_proportional_plan, twap_plan, vwap_proxy_plan
from src.config import load as load_config
from src.loader.loader import STOCK_NAMES, load_day
from src.models.m1_ac import solve_m1
from src.models.m2_lp import solve_m2
from src.models.m3_mip import solve_m3
from src.models.m4_ahp import ahp_consistency_ratio, ahp_weights
from src.models.rote_static import solve_rote_static
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

st.set_page_config(page_title="ROTE — Quantitative Execution", layout="wide")


@st.cache_data(show_spinner=False)
def cached_config() -> dict:
    return load_config()


@st.cache_data(show_spinner="Loading cached FI-2010 data…")
def cached_load_day(stock: str, day: int):
    return load_day(stock, day)


@st.cache_data(show_spinner=False)
def cached_calibration() -> dict[str, float]:
    path = Path("results/tables/calibration.json")
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): float(v) for k, v in raw.get("eta_0", {}).items()}


def order_size(theta: float, book: dict[str, np.ndarray]) -> float:
    """Return the protocol order size, Q = theta times mean visible ask depth."""
    return float(theta * np.mean(np.asarray(book["Da"], dtype=float)))


def visible_book_depth(book: dict[str, np.ndarray], snapshot_idx: int = 0) -> float:
    """Total ask liquidity displayed at one snapshot across the ten visible levels."""
    idx = min(max(snapshot_idx, 0), len(book["Va"]) - 1)
    return float(np.sum(np.asarray(book["Va"])[idx]))


def export_schedule(schedule: np.ndarray, model: str, order: Order) -> pd.DataFrame:
    shares = np.asarray(schedule, dtype=float)
    inventory = order.size - np.cumsum(shares)
    return pd.DataFrame(
        {
            "period": np.arange(1, len(shares) + 1),
            "shares": shares,
            "remaining_inventory": inventory,
        }
    ).assign(model=model)


def png_bytes(fig: plt.Figure) -> bytes:
    stream = io.BytesIO()
    fig.savefig(stream, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    return stream.getvalue()


def statistics_figure(book: dict[str, np.ndarray]) -> plt.Figure:
    n = len(book["M"])
    levels = np.arange(1, book["Va"].shape[1] + 1)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), dpi=140)
    axes[0, 0].plot(book["M"], color="#263238")
    axes[0, 0].set_title("Mid price")
    axes[0, 1].hist(np.asarray(book["S"]) / np.asarray(book["M"]) * 5000, bins=40)
    axes[0, 1].set_title("Half-spread distribution (bps)")
    axes[1, 0].plot(levels, np.mean(book["Va"], axis=0), label="ask")
    axes[1, 0].plot(levels, np.mean(book["Vb"], axis=0), label="bid")
    axes[1, 0].set_title("Mean depth by level")
    axes[1, 0].set_xlabel("Visible level")
    axes[1, 0].legend()
    returns = np.diff(np.log(np.maximum(book["M"], np.finfo(float).tiny)))
    axes[1, 1].hist(returns * 10000, bins=40)
    axes[1, 1].set_title("Event returns (bps)")
    for ax in axes.flat:
        ax.grid(alpha=0.25)
    fig.suptitle(f"Microstructure statistics ({n:,} snapshots)")
    fig.tight_layout()
    return fig


def interactive_book_figure(book: dict[str, np.ndarray], snapshot: int) -> go.Figure:
    levels = np.arange(1, book["Pa"].shape[1] + 1)
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=levels,
            y=book["Va"][snapshot],
            name="Ask volume",
            marker_color="#d95f02",
        )
    )
    figure.add_trace(
        go.Bar(
            x=levels,
            y=-book["Vb"][snapshot],
            name="Bid volume",
            marker_color="#1b9e77",
        )
    )
    figure.update_layout(
        title=f"Book depth at snapshot {snapshot:,}",
        xaxis_title="Visible level",
        yaxis_title="Shares",
        barmode="relative",
    )
    return figure


def interactive_schedule_figure(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame["period"],
            y=frame["remaining_inventory"],
            mode="lines+markers",
            name="Remaining inventory",
        )
    )
    figure.add_trace(go.Bar(x=frame["period"], y=frame["shares"], name="Shares"))
    figure.update_layout(
        title="Execution schedule and inventory",
        xaxis_title="Period",
        yaxis_title="Shares",
        hovermode="x unified",
    )
    return figure


def execution_params(
    cfg: dict,
    book: dict[str, np.ndarray],
    stock: str,
    horizon: int,
    omega: float,
    rho: float,
    fee: float = 0.0,
    lot: float = 50.0,
    max_tickets: int | None = None,
    phi: float | None = None,
) -> dict:
    stock_idx = STOCK_NAMES.index(stock) + 1
    calibration = cached_calibration()
    eta = calibration.get(str(stock_idx), float(np.median(list(calibration.values()) or [0.1])))
    stats = compute_statistics(book)
    sigma = max(float(stats["volatility_bps_per_period"]) / 10000.0, 1e-8)
    execution = cfg["execution"]
    resilience = execution["resilience"]
    return {
        "lambda_imp": 2.0 * eta * (np.cosh(omega) - 1.0) / sigma**2,
        "rho": rho,
        "eta": eta,
        "sigma": sigma,
        "sigma2": np.full(horizon, sigma**2),
        "c_f": fee,
        "L_min": lot,
        "K": max_tickets,
        "phi": resilience["base"] if phi is None else phi,
        "pi": execution["pi"],
    }


if "lob_slice" not in st.session_state:
    st.session_state.update(
        lob_slice=None,
        day=None,
        stock=None,
        compare_results=None,
        schedules_dict=None,
        schedule_df=None,
        schedule_figure=None,
        model_result=None,
    )

cfg = cached_config()
st.title("ROTE — Risk-Aware Optimal Trade Execution")
st.caption(
    "**Frozen Split Governance:** Calibration = Days 1–5 | Validation = Days 6–7 | "
    "Test = Days 8–9 (Gated) | Reserve = Day 10 (Protocol Locked)"
)
tabs = st.tabs(["1. Data", "2. Statistics", "3. Optimiser", "4. Compare", "5. Decision"])

with tabs[0]:
    st.header("Data Loader & LOB Ladder")
    stock = st.selectbox("Select Stock", STOCK_NAMES)
    day = st.slider("Select day", 1, 10, 1)
    if day >= 8:
        st.warning(
            "Days 8–9 are frozen test data. Day 10 is the reserve set and must not "
            "be used for tuning."
        )
        confirmed = st.checkbox("I confirm this is an evaluation-only test-set view.")
        if day == 10:
            confirmed = confirmed and st.checkbox("I additionally confirm reserve-day 10 usage.")
    else:
        confirmed = True
    if st.button("Load data", disabled=not confirmed):
        with st.spinner("Loading LOB data…"):
            lob_slice, loaded_day, measured = cached_load_day(stock, day)
        st.session_state.update(
            lob_slice=lob_slice,
            day=loaded_day,
            stock=stock,
            model_result=None,
            schedule_df=None,
            schedule_figure=None,
        )
        st.success(
            f"Loaded {stock}, day {day} ({'measured' if measured else 'frozen train'} boundary)."
        )
    if st.session_state.lob_slice is not None:
        book = st.session_state.lob_slice
        st.write(
            f"**Current dataset:** {st.session_state.stock}, day {st.session_state.day} · "
            f"{len(book['M']):,} events"
        )
        snapshot = st.slider("Book snapshot", 0, max(0, len(book["M"]) - 1), 0)
        fig = plot_lob_ladder(book, snapshot_idx=snapshot)
        st.pyplot(fig)
        st.download_button("Download ladder PNG", png_bytes(fig), "lob_ladder.png", "image/png")
        st.plotly_chart(interactive_book_figure(book, snapshot), use_container_width=True)

with tabs[1]:
    st.header("Descriptive Statistics & Microstructure Analytics")
    if st.session_state.lob_slice is None:
        st.warning("Load data in the Data tab first.")
    else:
        book = st.session_state.lob_slice
        stats = compute_statistics(book, rows_per_period=cfg["period"]["rows_per_period"])
        cols = st.columns(4)
        cols[0].metric("Mean half-spread", f"{stats['avg_half_spread_bps']:.2f} bps")
        cols[1].metric("Mean ask depth", f"{stats['avg_depth_ask']:,.0f}")
        cols[2].metric("Mean bid depth", f"{stats['avg_depth_bid']:,.0f}")
        cols[3].metric("Volatility", f"{stats['volatility_bps_per_period']:.2f} bps")
        fig = statistics_figure(book)
        st.pyplot(fig)
        st.download_button("Download statistics PNG", png_bytes(fig), "statistics.png", "image/png")
        mid_price = pd.DataFrame({"snapshot": np.arange(len(book["M"])), "mid": book["M"]})
        st.plotly_chart(
            go.Figure(
                go.Scatter(
                    x=mid_price["snapshot"],
                    y=mid_price["mid"],
                    mode="lines",
                    name="Mid price",
                )
            ).update_layout(title="Interactive mid-price history", hovermode="x unified"),
            use_container_width=True,
        )
        st.pyplot(plot_microstructure_analytics(book, max_points=350))

with tabs[2]:
    st.header("Mathematical Optimization Models")
    if st.session_state.lob_slice is None:
        st.warning("Load data in the Data tab first.")
    else:
        book = st.session_state.lob_slice
        execution = cfg["execution"]
        model = st.selectbox(
            "Model",
            [
                "M1 (Almgren-Chriss)",
                "M2 (LOB LP)",
                "M3 (Fixed-Charge MIP)",
                "ROTE-Static",
                "TWAP",
                "Depth-Proportional",
                "VWAP (Proxy)",
            ],
        )
        theta = st.select_slider(
            "Order-size θ (Q = θ × mean depth)",
            options=execution["theta"],
            value=execution["confirmatory_theta"],
        )
        max_horizon = max(1, len(book["M"]) // cfg["period"]["rows_per_period"])
        default_horizon = min(cfg["period"]["horizon"], max_horizon)
        horizon = st.slider("Execution horizon (periods)", 1, max_horizon, default_horizon)
        omega = st.select_slider(
            "Risk level ω",
            options=execution["omega_grid"],
            value=execution["risk_levels"]["medium"],
        )
        rho = st.slider("Participation cap ρ", 0.05, 1.0, float(execution["rho"]))
        fee = st.slider("M3 fixed fee c_f", 0.0, 20.0, 0.0, step=0.5)
        lot = st.number_input("M3 minimum lot", min_value=0.0, value=50.0, step=10.0)
        max_tickets = st.number_input("M3 maximum tickets", min_value=1, value=horizon, step=1)
        phi = st.slider("M3 resilience φ", 0.0, 1.0, float(execution["resilience"]["base"]))
        Q = order_size(float(theta), book)
        st.metric("Protocol order size Q", f"{Q:,.0f} shares")
        if visible_book_depth(book) < Q:
            st.warning(
                "Q exceeds the visible ask book at the selected snapshot; terminal "
                "sweep/penalty may apply."
            )
        order = Order(side="buy", size=Q, horizon=horizon, params={})
        rows = horizon * cfg["period"]["rows_per_period"]
        if len(book["M"]) < rows:
            st.error("The selected horizon exceeds the loaded day.")
        elif st.button("Run model"):
            sampled = {
                key: value[: rows : cfg["period"]["rows_per_period"]] for key, value in book.items()
            }
            params = execution_params(
                cfg,
                sampled,
                st.session_state.stock,
                horizon,
                float(omega),
                rho,
                fee,
                lot,
                int(max_tickets),
                phi,
            )
            try:
                if model.startswith("M1"):
                    schedule = solve_m1(order, sampled, params)
                elif model.startswith("M2"):
                    schedule = solve_m2(order, sampled, params)
                elif model.startswith("M3"):
                    schedule = solve_m3(order, sampled, params)
                elif model == "ROTE-Static":
                    schedule = solve_rote_static(order, sampled, params)
                elif model == "TWAP":
                    schedule = twap_plan(order)
                elif model == "VWAP (Proxy)":
                    schedule = vwap_proxy_plan(order, sampled)
                else:
                    schedule = depth_proportional_plan(order, sampled)
                st.session_state.model_result = (model, order, sampled, params, schedule)
            except Exception as exc:
                st.error(f"Solver error: {exc}")
        if st.session_state.model_result is not None:
            result_model, result_order, result_book, result_params, schedule = (
                st.session_state.model_result
            )
            frame = export_schedule(schedule.shares, result_model, result_order)
            st.session_state.schedule_df = frame
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(frame["period"], frame["remaining_inventory"], label="remaining inventory")
            ax.step(frame["period"], frame["shares"], where="mid", label="shares")
            ax.set_xlabel("Period")
            ax.grid(alpha=0.25)
            ax.legend()
            fig.tight_layout()
            st.session_state.schedule_figure = fig
            st.dataframe(frame, hide_index=True)
            st.plotly_chart(interactive_schedule_figure(frame), use_container_width=True)
            st.download_button(
                "Download schedule CSV", frame.to_csv(index=False), "schedule.csv", "text/csv"
            )
            st.download_button("Download schedule PNG", png_bytes(fig), "schedule.png", "image/png")
            if result_model.startswith("M1"):
                diagnostic, _ = plot_m1_frontier(result_order, result_book)
                st.pyplot(diagnostic)
            elif result_model.startswith("M2") or result_model == "ROTE-Static":
                st.pyplot(plot_m2_diagnostics(result_order, result_book, rho=rho))
            elif result_model.startswith("M3"):
                st.pyplot(plot_m3_tradeoff(result_order, result_book))
            st.success(f"{result_model} completed.")

with tabs[3]:
    st.header("Comparative Benchmark Evaluation")
    if st.session_state.lob_slice is None:
        st.warning("Load data in the Data tab first.")
    else:
        book = st.session_state.lob_slice
        theta = st.select_slider(
            "Comparison θ",
            options=cfg["execution"]["theta"],
            value=cfg["execution"]["confirmatory_theta"],
            key="compare_theta",
        )
        horizon = cfg["period"]["horizon"]
        Q = order_size(float(theta), book)
        rows = horizon * cfg["period"]["rows_per_period"]
        if len(book["M"]) < rows:
            st.error("Not enough events for the configured comparison horizon.")
        elif st.button("Run comparison"):
            sampled = {
                key: value[: rows : cfg["period"]["rows_per_period"]] for key, value in book.items()
            }
            order = Order(side="buy", size=Q, horizon=horizon, params={})
            params = execution_params(
                cfg,
                sampled,
                st.session_state.stock,
                horizon,
                cfg["execution"]["risk_levels"]["medium"],
                cfg["execution"]["rho"],
            )
            models = {
                "M1": solve_m1(order, sampled, params),
                "M2": solve_m2(order, sampled, params),
                "M3": solve_m3(order, sampled, params),
                "ROTE-Static": solve_rote_static(order, sampled, params),
                "TWAP": twap_plan(order),
                "Depth-Prop": depth_proportional_plan(order, sampled),
                "VWAP Proxy": vwap_proxy_plan(order, sampled),
            }
            records = []
            for name, plan in models.items():
                rep = simulate(plan, sampled, params)
                comp_pct = max(0.0, min(100.0, (1.0 - rep.unfilled_shares / max(Q, 1e-6)) * 100.0))
                records.append(
                    {
                        "Model": name,
                        "Shortfall (bps)": rep.shortfall_bps,
                        "Risk (std)": rep.std,
                        "Trades": rep.trades,
                        "Unfilled (shares)": rep.unfilled_shares,
                        "Completion (%)": comp_pct,
                    }
                )
            st.session_state.compare_results = pd.DataFrame(records)
            st.session_state.schedules_dict = {name: plan.shares for name, plan in models.items()}
        if st.session_state.compare_results is not None:
            st.dataframe(st.session_state.compare_results, hide_index=True)
            fig = plot_benchmark_frontier(
                st.session_state.compare_results, st.session_state.schedules_dict
            )
            st.pyplot(fig)
            st.plotly_chart(
                go.Figure(
                    go.Scatter(
                        x=st.session_state.compare_results["Risk (std)"],
                        y=st.session_state.compare_results["Shortfall (bps)"],
                        text=st.session_state.compare_results["Model"],
                        mode="markers+text",
                        textposition="top center",
                    )
                ).update_layout(
                    title="Interactive risk-cost frontier",
                    xaxis_title="Risk (std)",
                    yaxis_title="Shortfall (bps)",
                ),
                use_container_width=True,
            )

with tabs[4]:
    st.header("Decision Support (M4 AHP) & Reporting")
    if st.session_state.compare_results is None:
        st.warning("Run the comparison first.")
    else:
        st.subheader("Four-criterion pairwise preferences")
        saaty = list(range(1, 10))
        pair_cost_risk = st.select_slider("Cost vs risk", saaty, value=2)
        pair_cost_completion = st.select_slider("Cost vs completion", saaty, value=3)
        pair_cost_simplicity = st.select_slider("Cost vs simplicity", saaty, value=4)
        pair_risk_completion = st.select_slider("Risk vs completion", saaty, value=2)
        pair_risk_simplicity = st.select_slider("Risk vs simplicity", saaty, value=3)
        pair_completion_simplicity = st.select_slider("Completion vs simplicity", saaty, value=2)
        matrix = np.array(
            [
                [
                    1,
                    pair_cost_risk,
                    pair_cost_completion,
                    pair_cost_simplicity,
                ],
                [
                    1 / pair_cost_risk,
                    1,
                    pair_risk_completion,
                    pair_risk_simplicity,
                ],
                [
                    1 / pair_cost_completion,
                    1 / pair_risk_completion,
                    1,
                    pair_completion_simplicity,
                ],
                [
                    1 / pair_cost_simplicity,
                    1 / pair_risk_simplicity,
                    1 / pair_completion_simplicity,
                    1.0,
                ],
            ]
        )
        cr, consistent = ahp_consistency_ratio(matrix)
        st.info(
            f"Saaty consistency ratio: {cr:.3f} ({'consistent' if consistent else 'inconsistent'})"
        )
        weights = ahp_weights(matrix)
        df = st.session_state.compare_results.copy()
        # 1. Cost: lower shortfall is preferred
        min_cost = df["Shortfall (bps)"].min()
        cost_offset = max(0.0, -min_cost) + 1.0
        cost_utility = 1.0 / (df["Shortfall (bps)"] + cost_offset)
        df["norm_cost"] = cost_utility / cost_utility.sum()

        # 2. Risk: lower variance/std is preferred
        risk_utility = 1.0 / (df["Risk (std)"].abs() + 1e-4)
        df["norm_risk"] = risk_utility / risk_utility.sum()

        # 3. Completion: higher completion percentage is preferred
        comp_utility = df["Completion (%)"].clip(lower=0.1)
        df["norm_completion"] = comp_utility / comp_utility.sum()

        # 4. Simplicity: fewer trades is preferred
        simp_utility = 1.0 / (df["Trades"].clip(lower=1))
        df["norm_simp"] = simp_utility / simp_utility.sum()

        df["Score"] = (
            df["norm_cost"] * weights[0]
            + df["norm_risk"] * weights[1]
            + df["norm_completion"] * weights[2]
            + df["norm_simp"] * weights[3]
        )
        df = df.sort_values("Score", ascending=False)
        st.pyplot(plot_ahp_ranking(weights, df))
        st.success(f"Optimal strategy selected by AHP: **{df.iloc[0]['Model']}**")
