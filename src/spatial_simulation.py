from __future__ import annotations

import numpy as np
import pandas as pd


def _zscore(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce").astype(float)
    med = x.median()
    x = x.fillna(med)
    sd = x.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(np.zeros(len(x)), index=x.index)
    return (x - x.mean()) / sd


def add_growth_capacity_score(tracts: pd.DataFrame) -> pd.DataFrame:
    """Create a transparent tract-level growth-capacity score.

    This is a *scenario allocation device*, not a claim about neighborhood quality.
    It combines housing slack, transit service, income, and housing-cost pressure so
    metro population changes can be distributed spatially for experiments.
    """
    df = tracts.copy()

    pop = pd.to_numeric(df.get("population"), errors="coerce").clip(lower=1)
    hu = pd.to_numeric(df.get("housing_units"), errors="coerce").clip(lower=1)
    vacant = pd.to_numeric(df.get("vacant_units"), errors="coerce").fillna(0)
    income = pd.to_numeric(df.get("median_household_income"), errors="coerce")
    rent = pd.to_numeric(df.get("median_gross_rent"), errors="coerce")
    departures = pd.to_numeric(df.get("weekday_departures", 0), errors="coerce").fillna(0)

    df["vacancy_rate"] = (vacant / hu).clip(0, 0.6)
    df["transit_departures_per_1000"] = departures / pop * 1000
    df["rent_income_ratio"] = ((rent * 12) / income).replace([np.inf, -np.inf], np.nan)

    # Transparent, editable scenario weights; no normative interpretation intended.
    df["growth_capacity_score"] = (
        0.30 * _zscore(df["vacancy_rate"])
        + 0.25 * _zscore(np.log1p(df["transit_departures_per_1000"]))
        + 0.20 * _zscore(income)
        - 0.25 * _zscore(df["rent_income_ratio"])
    )
    return df


def simulate_tract_redistribution(
    metro_sim: pd.DataFrame,
    tracts: pd.DataFrame,
    redistribution_strength: float = 0.12,
    annual_noise: float = 0.015,
    seed: int = 42,
) -> pd.DataFrame:
    """Allocate a metro population trajectory across Census tracts.

    Shares update gradually from the observed baseline rather than allowing the
    scenario score to instantly dominate. Every simulated year reconciles exactly
    to the metro population total.
    """
    rng = np.random.default_rng(seed)
    base = add_growth_capacity_score(tracts)
    base = base.dropna(subset=["GEOID", "population"]).copy()
    base["population"] = pd.to_numeric(base["population"], errors="coerce").clip(lower=0)

    total = base["population"].sum()
    if total <= 0:
        raise ValueError("tract population must sum to a positive value")

    shares = (base["population"] / total).to_numpy(float)
    score = base["growth_capacity_score"].to_numpy(float)
    geoids = base["GEOID"].astype(str).to_numpy()
    county = base.get("COUNTYFP", pd.Series([None] * len(base))).astype(str).to_numpy()

    rows = []
    for i, r in metro_sim.reset_index(drop=True).iterrows():
        year = int(r["year"])
        metro_pop = float(r["population"])

        if i > 0:
            shock = rng.normal(0, annual_noise, len(shares))
            desirability = np.exp(np.clip(redistribution_strength * score + shock, -1.5, 1.5))
            target = shares * desirability
            target = target / target.sum()
            # Inertia prevents unrealistic one-year jumps in spatial population shares.
            shares = 0.88 * shares + 0.12 * target
            shares = shares / shares.sum()

        tract_pop = shares * metro_pop
        for g, c, p, s, sc in zip(geoids, county, tract_pop, shares, score):
            rows.append({
                "year": year,
                "GEOID": g,
                "COUNTYFP": c,
                "population": float(p),
                "share_of_metro": float(s),
                "growth_capacity_score": float(sc),
            })

    return pd.DataFrame(rows)
