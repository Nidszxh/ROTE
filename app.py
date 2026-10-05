from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

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

st.set_page_config(page_title="ROTE — Quantitative Execution", layout="wide")
st.title("ROTE — Risk-Aware Optimal Trade Execution")

if "lob_slice" not in st.session_state:
    st.session_state.lob_slice = None
    st.session_state.day = None
    st.session_state.stock = None

tabs = st.tabs(["1. Data", "2. Statistics", "3. Optimiser", "4. Compare", "5. Decision"])

# ---------------------------------------------------------
# Tab 1: Data Loader & LOB Ladder
# ---------------------------------------------------------
with tabs[0]:
    st.header("Data Loader & Order Book Visualizer")
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        stock = st.selectbox("Select Stock", STOCK_NAMES)
    with col_sel2:
        day = st.slider("Select Day", min_value=1, max_value=10, value=1)

    if st.button("Load Data"):
        with st.spinner("Loading LOB data..."):
            lob_slice, d, is_measured = load_day(stock, day)
            st.session_state.lob_slice = lob_slice
            st.session_state.day = d
            st.session_state.stock = stock
            st.success(f"Loaded {stock} for day {day}")
            st.info(f"Boundary measured: {is_measured}")

    if st.session_state.lob_slice is not None:
        st.write(f"**Current Dataset**: {st.session_state.stock} (Day {st.session_state.day})")
        st.write(f"**Total Events**: {len(st.session_state.lob_slice['M']):,}")

        st.subheader("10-Level Order Book Depth & Price Ladder")
        fig_ladder = plot_lob_ladder(st.session_state.lob_slice, snapshot_idx=100)
        st.pyplot(fig_ladder)
        plt.close(fig_ladder)

# ---------------------------------------------------------
# Tab 2: Descriptive Statistics & Analytics
# ---------------------------------------------------------
with tabs[1]:
    st.header("Descriptive Statistics & Microstructure Analytics")
    if st.session_state.lob_slice is not None:
        stats = compute_statistics(st.session_state.lob_slice)
        col1, col2 = st.columns(2)
        col1.metric("Average Half Spread", f"{stats['avg_half_spread_bps']:.2f} bps")
        col1.metric("Average Ask Depth", f"{stats['avg_depth_ask']:,.0f} shares")
        col2.metric("Average Imbalance", f"{stats['avg_imbalance']:.4f}")
        col2.metric("Volatility (per 20 rows)", f"{stats['volatility_bps_per_period']:.2f} bps")

        st.subheader("Microstructure Dynamics: Imbalance, Spread & Depth")
        fig_micro = plot_microstructure_analytics(st.session_state.lob_slice, max_points=350)
        st.pyplot(fig_micro)
        plt.close(fig_micro)
    else:
        st.warning("Please load data in the Data tab.")

# ---------------------------------------------------------
# Tab 3: Optimiser
# ---------------------------------------------------------
with tabs[2]:
    st.header("Mathematical Optimization Models")
    if st.session_state.lob_slice is not None:
        model = st.selectbox(
            "Select Model",
            [
                "M1 (Almgren-Chriss)",
                "M2 (LOB LP)",
                "M3 (Fixed-Charge MIP)",
                "TWAP",
                "Depth-Proportional",
                "VWAP (Proxy)",
            ],
        )

        col1, col2 = st.columns(2)
        with col1:
            Q = st.number_input("Order Size (Shares)", min_value=100.0, value=5000.0, step=500.0)
            T = st.slider(
                "Execution Horizon (T periods of 20 rows)", min_value=5, max_value=60, value=20
            )
        with col2:
            lam = st.slider(
                "Risk Aversion (lambda)", min_value=0.0, max_value=0.5, value=0.05, step=0.01
            )
            rho = st.slider("Participation Cap (rho)", min_value=0.05, max_value=1.0, value=0.25)

        order = Order(side="buy", size=Q, horizon=T, params={})
        step = 20
        T_rows = T * step
        lob = st.session_state.lob_slice

        if len(lob["M"]) < T_rows:
            st.error("Not enough rows in dataset for this horizon.")
        else:
            book = {k: v[:T_rows:step] for k, v in lob.items()}
            params = {
                "lambda_imp": lam,
                "rho": rho,
                "eta": 0.1,
                "sigma": 0.015,
                "sigma2": np.ones(T) * 0.015,
                "c_f": 5.0,
                "L_min": 50.0,
            }

            if st.button("Run Model"):
                with st.spinner("Solving optimization model..."):
                    try:
                        if model == "M1 (Almgren-Chriss)":
                            sched = solve_m1(order, book, params)
                        elif model == "M2 (LOB LP)":
                            sched = solve_m2(order, book, params)
                        elif model == "M3 (Fixed-Charge MIP)":
                            sched = solve_m3(order, book, params)
                        elif model == "TWAP":
                            sched = twap_plan(order)
                        elif model == "VWAP (Proxy)":
                            st.info("Using imbalance-weighted proxy for event-time VWAP.")
                            sched = vwap_proxy_plan(order, book)
                        else:
                            sched = depth_proportional_plan(order, book)

                        st.subheader(f"Optimal Execution Schedule ({model})")
                        st.line_chart(sched.shares)

                        # Model-specific deep dive diagnostics
                        if model == "M1 (Almgren-Chriss)":
                            st.subheader("M1 Efficient Frontier & Schedule Comparison")
                            fig_m1, _ = plot_m1_frontier(order, book)
                            st.pyplot(fig_m1)
                            plt.close(fig_m1)
                        elif model == "M2 (LOB LP)":
                            st.subheader("M2 LOB Allocation & Shadow Price Diagnostics")
                            fig_m2 = plot_m2_diagnostics(order, book, rho=rho)
                            st.pyplot(fig_m2)
                            plt.close(fig_m2)
                        elif model == "M3 (Fixed-Charge MIP)":
                            st.subheader("M3 Child Order Sparsity vs Fixed Ticket Fees")
                            fig_m3 = plot_m3_tradeoff(order, book)
                            st.pyplot(fig_m3)
                            plt.close(fig_m3)

                        st.success("Optimization completed successfully.")
                    except Exception as exc:
                        st.error(f"Solver Error: {exc}")
                        st.info(
                            "Tip: If the problem is infeasible, try increasing horizon (T), "
                            "raising participation cap (rho), or lowering order size."
                        )
    else:
        st.warning("Please load data in the Data tab.")

# ---------------------------------------------------------
# Tab 4: Compare Benchmarks
# ---------------------------------------------------------
with tabs[3]:
    st.header("Comparative Benchmark Evaluation")
    if st.session_state.lob_slice is not None:
        if st.button("Run Comprehensive Comparison"):
            Q_comp = 5000.0
            T_comp = 20
            order_c = Order(side="buy", size=Q_comp, horizon=T_comp, params={})

            step = 20
            T_rows = T_comp * step
            lob = st.session_state.lob_slice
            book_c = {k: v[:T_rows:step] for k, v in lob.items()}
            params_c = {
                "lambda_imp": 0.05,
                "rho": 0.25,
                "eta": 0.1,
                "sigma": 0.015,
                "sigma2": np.ones(T_comp) * 0.015,
                "c_f": 5.0,
                "L_min": 50.0,
            }

            with st.spinner("Simulating and benchmarking all strategies..."):
                try:
                    models = {
                        "M1": solve_m1(order_c, book_c, params_c),
                        "M2": solve_m2(order_c, book_c, params_c),
                        "M3": solve_m3(order_c, book_c, params_c),
                        "TWAP": twap_plan(order_c),
                        "Depth-Prop": depth_proportional_plan(order_c, book_c),
                        "VWAP Proxy": vwap_proxy_plan(order_c, book_c),
                    }

                    results = []
                    schedules_dict = {}
                    for m_name, sched in models.items():
                        rep = simulate(sched, book_c)
                        results.append(
                            {
                                "Model": m_name,
                                "Shortfall (bps)": rep.shortfall_bps,
                                "Risk (std)": rep.std,
                                "Trades": rep.trades,
                            }
                        )
                        schedules_dict[m_name] = sched.shares

                    df = pd.DataFrame(results)
                    st.session_state.compare_results = df
                    st.session_state.schedules_dict = schedules_dict

                    st.table(df)

                    st.subheader("Strategy Trajectories & Empirical Risk-Cost Frontier")
                    fig_comp = plot_benchmark_frontier(df, schedules_dict)
                    st.pyplot(fig_comp)
                    plt.close(fig_comp)
                    st.success("Comparison completed.")
                except Exception as exc:
                    st.error(f"Comparison execution error: {exc}")
    else:
        st.warning("Please load data in the Data tab.")

# ---------------------------------------------------------
# Tab 5: Decision (M4 AHP) & Reporting
# ---------------------------------------------------------
with tabs[4]:
    st.header("Decision Support (M4 AHP) & Executive Reporting")
    if "compare_results" in st.session_state and "schedules_dict" in st.session_state:
        st.write("Using Analytic Hierarchy Process (AHP) to score and rank execution strategies.")

        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            w_cost = st.slider("Importance of Cost Minimization", 1, 9, 6)
        with col_w2:
            w_risk = st.slider("Importance of Timing Risk Reduction", 1, 9, 4)
        with col_w3:
            w_simp = st.slider("Importance of Operational Simplicity", 1, 9, 2)

        matrix = np.array(
            [
                [1.0, w_cost / w_risk, w_cost / w_simp],
                [w_risk / w_cost, 1.0, w_risk / w_simp],
                [w_simp / w_cost, w_simp / w_risk, 1.0],
            ]
        )

        cr, is_consistent = ahp_consistency_ratio(matrix)
        weights = ahp_weights(matrix)

        st.info(
            f"Saaty Consistency Ratio: **{cr:.3f}** "
            f"({'Consistent (CR < 0.10)' if is_consistent else 'Inconsistent (CR >= 0.10)'})"
        )

        df = st.session_state.compare_results.copy()
        df["norm_cost"] = 1.0 / (df["Shortfall (bps)"] + 1e-4)
        df["norm_risk"] = 1.0 / (df["Risk (std)"] + 1e-4)
        df["norm_simp"] = 1.0 / (df["Trades"] + 1e-4)

        for c in ["norm_cost", "norm_risk", "norm_simp"]:
            c_sum = df[c].sum()
            df[c] = df[c] / c_sum if c_sum > 0 else 0.0

        df["Score"] = (
            df["norm_cost"] * weights[0]
            + df["norm_risk"] * weights[1]
            + df["norm_simp"] * weights[2]
        )
        df = df.sort_values("Score", ascending=False)

        st.subheader("AHP Preference Breakdown & Strategy Rankings")
        fig_ahp = plot_ahp_ranking(weights, df)
        st.pyplot(fig_ahp)
        plt.close(fig_ahp)

        winner = df.iloc[0]["Model"]
        st.success(f"Optimal Strategy Selected by AHP: **{winner}**")

        st.divider()
        st.subheader("Executive Report Download")
        report_file = Path("results/MODEL_EXECUTION_REPORT.md")
        if report_file.exists():
            report_text = report_file.read_text(encoding="utf-8")
            st.download_button(
                label="Download Executive Model Execution Report (Markdown)",
                data=report_text,
                file_name="ROTE_Execution_Report.md",
                mime="text/markdown",
            )
    else:
        st.warning("Please run the Comparison tab first to populate strategy metrics.")
