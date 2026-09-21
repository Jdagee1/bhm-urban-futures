# Portfolio Brief — BHM Urban Futures

## One-line pitch
I built a Birmingham–Hoover urban-systems simulation that combines metropolitan forecasting, uncertainty analysis, spatial redistribution, transit accessibility, and machine-learning-based scenario discovery to investigate how a metro could change under many plausible futures.

## Why this project fits my career direction
A 160-question forced-choice career-interest exercise consistently pointed toward:

- urban data science / computational urban analysis;
- metropolitan rather than single-site thinking;
- spatial investigation and forecasting;
- integrated systems rather than isolated models;
- population and migration as major drivers;
- validation, uncertainty, vulnerability, thresholds, and early warning;
- scenario discovery instead of one deterministic narrative;
- applied technical evidence for real decisions;
- using sophisticated analytical systems more than maintaining software infrastructure.

## Interview walkthrough
1. **Start with the problem.** Cities are coupled systems: population, jobs, housing, infrastructure, and public services change at different speeds.
2. **Show the baseline.** The model calibrates population and labor-market behavior from public Birmingham–Hoover history.
3. **Show the simulator.** Change migration, job growth, housing supply, service capacity, infrastructure capacity, and volatility.
4. **Show uncertainty.** Run Monte Carlo futures rather than claiming one precise forecast.
5. **Show vulnerability.** Sample hundreds of parameter combinations and use machine learning to identify which combinations are associated with crossing a stress threshold.
6. **Show spatial thinking.** Fetch official Census tracts, ACS context, and MAX Transit GTFS, then allocate metro change across real geography.
7. **End with limitations.** Several subsystem relationships remain stylized; the responsible next step is empirical calibration and rolling backtests, not pretending the prototype is an official forecast.

## Technical stack
Python, pandas, NumPy, scikit-learn, GeoPandas, Shapely, Streamlit, Plotly, Matplotlib, GTFS, Census TIGER/Line, ACS, FRED, pytest, GitHub Actions.

## What this demonstrates to an employer
- end-to-end analytical project design;
- reproducible public-data pipelines;
- stochastic simulation;
- geospatial analytics;
- uncertainty quantification;
- scenario discovery / interpretable ML;
- dashboarding and stakeholder communication;
- model-risk awareness and documentation.
