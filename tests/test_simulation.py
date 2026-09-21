from pathlib import Path
import numpy as np

from src.model import load_history, calibrate, Scenario, simulate, run_monte_carlo
from src.spatial import load_county_history, allocate_metro_population

ROOT = Path(__file__).resolve().parents[1]

def test_simulation_outputs_are_finite():
    cal = calibrate(load_history(ROOT / "data" / "birmingham_msa_history.csv"))
    sim = simulate(cal, Scenario(years=5, seed=1))
    assert len(sim) == 6
    assert np.isfinite(sim["population"]).all()
    assert ((sim["system_stress"] >= 0) & (sim["system_stress"] <= 1)).all()

def test_counties_reconcile_to_metro_total():
    cal = calibrate(load_history(ROOT / "data" / "birmingham_msa_history.csv"))
    sim = simulate(cal, Scenario(years=5, seed=1))
    counties = load_county_history(ROOT / "data" / "msa_county_population_2021_2025.csv")
    spatial = allocate_metro_population(sim, counties, seed=1)
    check = spatial.groupby("year")["population"].sum().reset_index()
    merged = sim[["year", "population"]].merge(check, on="year", suffixes=("_metro","_county"))
    assert np.allclose(merged["population_metro"], merged["population_county"])
