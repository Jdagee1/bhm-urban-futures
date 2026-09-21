import numpy as np
import pandas as pd
from src.spatial_simulation import add_growth_capacity_score, simulate_tract_redistribution


def _tracts():
    return pd.DataFrame({
        "GEOID": ["1","2","3"],
        "COUNTYFP": ["073","073","117"],
        "population": [1000,2000,3000],
        "housing_units": [500,1000,1500],
        "vacant_units": [50,80,100],
        "median_household_income": [40000,60000,80000],
        "median_gross_rent": [900,1100,1300],
        "weekday_departures": [100,50,10],
    })


def test_growth_capacity_is_finite():
    out = add_growth_capacity_score(_tracts())
    assert np.isfinite(out["growth_capacity_score"]).all()


def test_spatial_totals_reconcile():
    metro = pd.DataFrame({"year":[2025,2026,2027],"population":[6000,6060,6120]})
    out = simulate_tract_redistribution(metro, _tracts(), seed=3)
    sums = out.groupby("year")["population"].sum().to_numpy()
    assert np.allclose(sums, metro["population"].to_numpy())
