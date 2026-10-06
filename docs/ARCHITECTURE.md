# ROTE architecture

ROTE is organized as a data-to-decision pipeline:

```text
FI-2010 archive
      |
      v
setup / manifest verification / processed cache
      |
      v
loader -> statistics and calibration
      |
      v
Order -> M1/M2/M3/M4 or benchmark -> Schedule
      |
      v
simulator -> CostReport
      |
      +--> Streamlit application
      +--> evaluation tables and confidence intervals
      +--> figures and Markdown reports
```

The loader excludes all five FI-2010 label rows. Raw files are kept outside version control,
while processed caches are disposable and reproducible from the archive and configuration.
Models consume the shared `Order` and `Schedule` contracts in `src/utils/contracts.py`.
