
from __future__ import annotations
from dataclasses import replace
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

from .model import Calibration, Scenario, simulate, first_threshold_year

FEATURES = [
    "migration_shift",
    "job_growth_shift",
    "housing_supply_growth",
    "housing_response",
    "service_capacity_growth",
    "infrastructure_growth",
    "volatility_scale",
]

def generate_experiments(
    cal: Calibration,
    base: Scenario,
    n: int = 600,
    seed: int = 404
) -> pd.DataFrame:
    """Sample plausible parameter combinations and record whether stress threshold is crossed."""
    rng = np.random.default_rng(seed)
    rows = []

    for i in range(n):
        values = {
            "migration_shift": rng.uniform(-0.008, 0.010),
            "job_growth_shift": rng.uniform(-0.015, 0.015),
            "housing_supply_growth": rng.uniform(-0.002, 0.020),
            "housing_response": rng.uniform(0.10, 1.20),
            "service_capacity_growth": rng.uniform(-0.002, 0.020),
            "infrastructure_growth": rng.uniform(-0.002, 0.020),
            "volatility_scale": rng.uniform(0.50, 1.80),
        }
        sc = replace(base, **values, seed=int(rng.integers(0, 2_000_000_000)))
        sim = simulate(cal, sc)
        threshold_year = first_threshold_year(sim)

        rows.append({
            **values,
            "threshold_crossed": int(np.isfinite(threshold_year)),
            "threshold_year": threshold_year,
            "max_stress": float(sim["system_stress"].max()),
            "ending_population": float(sim["population"].iloc[-1]),
        })

    return pd.DataFrame(rows)

def fit_vulnerability_model(experiments: pd.DataFrame, seed: int = 404):
    """Fit an explainable scenario-discovery classifier and return feature importance."""
    X = experiments[FEATURES]
    y = experiments["threshold_crossed"]

    if y.nunique() < 2:
        return None, pd.DataFrame({
            "feature": FEATURES,
            "importance": np.nan,
            "permutation_importance": np.nan
        })

    model = RandomForestClassifier(
        n_estimators=350,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X, y)

    perm = permutation_importance(
        model, X, y, n_repeats=10, random_state=seed, n_jobs=-1
    )

    imp = pd.DataFrame({
        "feature": FEATURES,
        "importance": model.feature_importances_,
        "permutation_importance": perm.importances_mean,
    }).sort_values("permutation_importance", ascending=False)

    return model, imp.reset_index(drop=True)
