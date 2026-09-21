from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.model import load_history, calibrate, Scenario, simulate, run_monte_carlo, first_threshold_year
from src.spatial import load_county_history, allocate_metro_population
from src.spatial_simulation import simulate_tract_redistribution, add_growth_capacity_score
from src.discovery import generate_experiments, fit_vulnerability_model

st.set_page_config(page_title="BHM Urban Futures", page_icon="🏙️", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.7rem; padding-bottom: 3rem;}
[data-testid="stMetricValue"] {font-size: 1.55rem;}
.small-note {color: #777; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)

st.title("BHM Urban Futures")
st.caption("Urban systems simulation • spatial forecasting • uncertainty • scenario discovery • Birmingham–Hoover, Alabama")

history = load_history(ROOT / "data" / "birmingham_msa_history.csv")
counties = load_county_history(ROOT / "data" / "msa_county_population_2021_2025.csv")
cal = calibrate(history)

with st.sidebar:
    st.header("Scenario laboratory")
    years = st.slider("Forecast horizon", 5, 30, 20)
    migration = st.slider("Migration shift (pp/yr)", -0.80, 1.00, 0.00, 0.05) / 100
    jobs = st.slider("Employment-growth shift (pp/yr)", -1.50, 1.50, 0.00, 0.05) / 100
    housing = st.slider("Housing-supply growth (%/yr)", -0.20, 2.00, 0.60, 0.05) / 100
    housing_response = st.slider("Housing supply responsiveness", 0.10, 1.20, 0.55, 0.05)
    services = st.slider("Public-service capacity growth (%/yr)", -0.20, 2.00, 0.50, 0.05) / 100
    infra = st.slider("Infrastructure capacity growth (%/yr)", -0.20, 2.00, 0.50, 0.05) / 100
    volatility = st.slider("Uncertainty multiplier", 0.50, 2.00, 1.00, 0.05)
    threshold = st.slider("System-stress warning threshold", 0.30, 0.80, 0.55, 0.01)
    seed = st.number_input("Random seed", min_value=1, max_value=999999, value=42)

scenario = Scenario(
    start_year=cal.base_year,
    years=years,
    migration_shift=migration,
    job_growth_shift=jobs,
    housing_supply_growth=housing,
    housing_response=housing_response,
    service_capacity_growth=services,
    infrastructure_growth=infra,
    volatility_scale=volatility,
    stress_threshold=threshold,
    seed=int(seed),
)
sim = simulate(cal, scenario)
threshold_year = first_threshold_year(sim)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("2025 population", f"{cal.population:,.0f}")
c2.metric("Scenario end", f"{sim['population'].iloc[-1]:,.0f}", f"{(sim['population'].iloc[-1]/cal.population-1):+.1%}")
c3.metric("Peak stress", f"{sim['system_stress'].max():.2f}")
c4.metric("Warning year", "None" if np.isnan(threshold_year) else str(int(threshold_year)))
c5.metric("End unemployment", f"{sim['unemployment_rate'].iloc[-1]:.1f}%")

tract_geojson = ROOT / "data" / "processed" / "birmingham_msa_tract_context.geojson"
tract_metrics = ROOT / "data" / "processed" / "birmingham_msa_tract_metrics.csv"

system_tab, spatial_tab, uncertainty_tab, discovery_tab, methods_tab = st.tabs([
    "System forecast", "Spatial change", "Uncertainty", "Vulnerability lab", "Methodology"
])

with system_tab:
    left, right = st.columns([1.15, 0.85])
    with left:
        st.subheader("Metropolitan trajectory")
        st.line_chart(sim.set_index("year")[["population","employment"]])
    with right:
        st.subheader("System warning signals")
        st.line_chart(sim.set_index("year")[["system_stress","structural_mismatch"]])
    st.subheader("Subsystem gaps")
    st.line_chart(sim.set_index("year")[["housing_pressure","service_gap","infrastructure_gap","fiscal_gap"]])
    st.dataframe(sim[["year","population","employment","unemployment_rate","house_price_index","system_stress","state"]].tail(12), use_container_width=True)

with spatial_tab:
    st.subheader("Where metropolitan change could redistribute")
    if tract_geojson.exists() and tract_metrics.exists():
        import geopandas as gpd
        import plotly.express as px

        gdf = gpd.read_file(tract_geojson)
        metrics = pd.read_csv(tract_metrics, dtype={"GEOID": str})
        base = add_growth_capacity_score(metrics)
        tract_sim = simulate_tract_redistribution(sim, base, seed=int(seed))
        selected_year = st.slider("Map year", int(sim["year"].min()), int(sim["year"].max()), int(sim["year"].max()))
        selected = tract_sim[tract_sim["year"] == selected_year][["GEOID","population","share_of_metro","growth_capacity_score"]]
        mapdf = gdf.merge(selected, on="GEOID", how="left")

        metric = st.selectbox("Map layer", ["population","growth_capacity_score","weekday_departures","median_household_income","vacancy_rate"], index=0)
        if "vacancy_rate" not in mapdf.columns:
            mapdf["vacancy_rate"] = mapdf["vacant_units"] / mapdf["housing_units"].replace(0, np.nan)

        fig = px.choropleth_map(
            mapdf,
            geojson=json.loads(mapdf.to_json()),
            locations=mapdf.index,
            color=metric,
            hover_name="NAMELSAD",
            hover_data={"county": True, "GEOID": True},
            map_style="carto-positron",
            center={"lat":33.52,"lon":-86.81},
            zoom=8.4,
            opacity=0.72,
            height=650,
        )
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Tract allocation is a scenario model constrained to the metro total; it is not an official tract forecast.")
    else:
        st.info("Real tract GIS + ACS + MAX Transit layers are wired into the project but not committed as large raw files. Run `python scripts/prepare_flagship_data.py` once, then reload this app.")
        spatial = allocate_metro_population(sim, counties, seed=int(seed))
        st.line_chart(spatial.pivot(index="year", columns="county", values="population"))
        st.caption("Immediate fallback: seven-county population allocation using bundled public county history.")

with uncertainty_tab:
    st.subheader("Monte Carlo uncertainty")
    n = st.slider("Simulation runs", 100, 1500, 400, 50, key="mc")
    if st.button("Run uncertainty analysis", type="primary"):
        with st.spinner("Running stochastic futures..."):
            _, summary = run_monte_carlo(cal, scenario, n=n, seed=int(seed)+100)
        fig, ax = plt.subplots(figsize=(9,4.8))
        ax.fill_between(summary["year"], summary["population_p10"], summary["population_p90"], alpha=.2)
        ax.plot(summary["year"], summary["population_p50"], linewidth=2)
        ax.set_title("Population: median and 10th–90th percentile range")
        ax.set_xlabel("Year"); ax.set_ylabel("Population"); ax.grid(alpha=.25)
        st.pyplot(fig)
        st.line_chart(summary.set_index("year")[["threshold_probability"]])
        st.dataframe(summary.tail(10), use_container_width=True)

with discovery_tab:
    st.subheader("Scenario discovery: what combinations create vulnerability?")
    st.write("Rather than choose a few narratives, this lab samples many plausible combinations and learns which conditions are most associated with crossing the system-stress threshold.")
    n_exp = st.slider("Scenario experiments", 200, 2000, 700, 100)
    if st.button("Run vulnerability lab", type="primary"):
        with st.spinner("Exploring scenario space..."):
            ex = generate_experiments(cal, scenario, n=n_exp, seed=int(seed)+200)
            _, imp = fit_vulnerability_model(ex, seed=int(seed)+200)
        a,b,c = st.columns(3)
        a.metric("Threshold-crossing experiments", f"{ex['threshold_crossed'].mean():.1%}")
        b.metric("Median maximum stress", f"{ex['max_stress'].median():.2f}")
        c.metric("Median ending population", f"{ex['ending_population'].median():,.0f}")
        st.bar_chart(imp.set_index("feature")[["permutation_importance"]])
        st.dataframe(imp, use_container_width=True)

with methods_tab:
    st.subheader("What is observed vs. modeled")
    st.markdown("""
**Observed public inputs:** Birmingham–Hoover population, employment, unemployment; recent seven-county population; optional 2024 TIGER/Line Census tracts; optional ACS tract demographics/housing; optional MAX static GTFS; optional FHFA house-price index and Census building-permit series via FRED.

**Modeled / stylized components:** cross-system feedback coefficients, indexed public-service capacity, indexed infrastructure capacity, indexed fiscal capacity, structural mismatch, composite stress, and tract redistribution weights.

**Core principle:** the app is designed to expose uncertainty and assumptions rather than hide them. It supports scenario discovery and applied decision support, not official forecasting or automatic policy recommendations.
""")
    st.code("python scripts/prepare_flagship_data.py\nstreamlit run app.py", language="bash")

st.divider()
st.caption("BHM Urban Futures is a portfolio-grade exploratory simulation. Conditional scenarios are not official forecasts or policy recommendations.")
