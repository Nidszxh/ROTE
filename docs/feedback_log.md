# Review 1 Feedback Log

1. **Normalised Data Constraints**: Real prices and sizes may not be recoverable due to FI-2010 Z-score normalisation.
   - *Action*: Work in relative units (ticks, bps, normalised depth) and state this explicitly in the assumptions.
2. **Event Time vs Calendar Time**: The dataset records events rather than continuous timestamps.
   - *Action*: The schedule must run on event time ("trade X over N book events") and benchmarks must adapt accordingly.
3. **Market Impact Assumption**: The backtest cannot show the market's reaction to our own orders since recorded data doesn't react.
   - *Action*: State the assumption clearly. Walk the recorded book for immediate cost, and add a calibrated impact model for the rest.
4. **VWAP feasibility**: VWAP requires a volume clock which is unavailable due to event-time.
   - *Action*: Substitute VWAP with TWAP and Depth-Proportional schedules, providing a defensible justification.
5. **UI and Deliverable Formats**: Ensure the Streamlit UI contains Data, Statistics, Optimiser, Compare, and Decision tabs.
   - *Action*: Scaffold Streamlit app strictly following the 5-tab format.

---

## Post-Review 1 Implementation & Verification Status

All five review-1 feedback items have been fully addressed, integrated, and verified in the codebase:
- **Normalised Units**: Operationalized in basis points, ticks, and normalized depth throughout the data loader, stats, models, and UI.
- **Event-Time Execution**: All horizons $T$ are indexed by discrete order-book events with exact integer step slicing.
- **Market Reaction Transparency**: Replay walk-the-book clearing paired with calibrated empirical impact models ($\eta_0, \phi, \pi$) and documented caveats.
- **VWAP Benchmark**: Implemented an Imbalance-Weighted Volume Proxy with clear UI transparency disclaimers.
- **5-Tab UI Platform**: Fully functional Streamlit app with rich visual components and executive report export.

