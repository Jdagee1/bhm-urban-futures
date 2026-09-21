
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

def load_county_history(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path).sort_values(["county", "year"]).reset_index(drop=True)

def county_momentum(county_history: pd.DataFrame) -> pd.DataFrame:
    """Estimate recent county growth momentum from the bundled 2021-2025 data."""
    rows = []
    for county, g in county_history.groupby("county"):
        g = g.sort_values("year")
        start = float(g["population_thousands"].iloc[0])
        end = float(g["population_thousands"].iloc[-1])
        years = int(g["year"].iloc[-1] - g["year"].iloc[0])
        cagr = (end / start) ** (1 / years) - 1 if years > 0 else 0.0
        rows.append({
            "county": county,
            "base_population": end * 1000,
            "recent_cagr": cagr
        })
    return pd.DataFrame(rows)

def allocate_metro_population(
    metro_sim: pd.DataFrame,
    county_history: pd.DataFrame,
    convergence: float = 0.35,
    noise: float = 0.0015,
    seed: int = 42
) -> pd.DataFrame:
    """Allocate metro population across the seven MSA counties.

    County shares evolve using recent population momentum plus partial
    convergence toward metro growth. Annual county totals are rescaled so
    they sum exactly to the metro simulation total.
    """
    rng = np.random.default_rng(seed)
    momentum = county_momentum(county_history)
    counties = momentum["county"].tolist()
    pops = dict(zip(momentum["county"], momentum["base_population"]))
    recent = dict(zip(momentum["county"], momentum["recent_cagr"]))

    base_year = int(metro_sim["year"].min())
    out = []

    for _, metro_row in metro_sim.iterrows():
        year = int(metro_row["year"])
        metro_pop = float(metro_row["population"])
        metro_g = float(metro_row.get("population_growth", 0.0))

        if year > base_year:
            for c in counties:
                county_g = (
                    (1 - convergence) * recent[c]
                    + convergence * metro_g
                    + rng.normal(0, noise)
                )
                county_g = float(np.clip(county_g, -0.03, 0.04))
                pops[c] *= (1 + county_g)

        scale = metro_pop / sum(pops.values())
        for c in counties:
            pops[c] *= scale
            out.append({
                "year": year,
                "county": c,
                "population": pops[c],
                "share_of_msa": pops[c] / metro_pop
            })

    return pd.DataFrame(out)
