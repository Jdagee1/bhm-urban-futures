
from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
import numpy as np
import pandas as pd

@dataclass
class Calibration:
    base_year: int
    population: float
    employment: float
    unemployment_rate: float
    pop_growth: float
    job_growth: float
    pop_volatility: float
    job_volatility: float
    hpi: float = 311.08

@dataclass
class Scenario:
    start_year: int = 2025
    years: int = 20

    # Scenario levers (annual rates expressed as decimals)
    migration_shift: float = 0.0000
    job_growth_shift: float = 0.0000
    housing_supply_growth: float = 0.0060
    housing_response: float = 0.55
    service_capacity_growth: float = 0.0050
    infrastructure_growth: float = 0.0050
    volatility_scale: float = 1.00

    # Behavioral / system coefficients
    pop_job_elasticity: float = 0.20
    housing_cost_penalty: float = 0.10
    housing_price_elasticity: float = 0.45
    macro_persistence: float = 0.45
    stress_threshold: float = 0.55

    seed: int = 42

def load_history(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df.sort_values("year").reset_index(drop=True)

def calibrate(history: pd.DataFrame) -> Calibration:
    """Robustly estimate baseline annual growth/volatility from the bundled history.

    Large one-year discontinuities are clipped/excluded to reduce sensitivity to
    shocks, revisions, and geography-definition breaks.
    """
    df = history.copy()
    df["pop_growth"] = df["population_thousands"].pct_change()
    df["job_growth"] = df["employment_persons"].pct_change()

    pop = df.loc[df["pop_growth"].abs() <= 0.03, "pop_growth"].dropna()
    jobs = df.loc[df["job_growth"].abs() <= 0.04, "job_growth"].dropna()

    recent = df.tail(5)
    return Calibration(
        base_year=int(df["year"].iloc[-1]),
        population=float(df["population_thousands"].iloc[-1] * 1000),
        employment=float(df["employment_persons"].iloc[-1]),
        unemployment_rate=float(recent["unemployment_rate_pct"].median()),
        pop_growth=float(pop.median()),
        job_growth=float(jobs.median()),
        pop_volatility=float(max(pop.std(ddof=1), 0.0025)),
        job_volatility=float(max(jobs.std(ddof=1), 0.0060)),
    )

def _clip_rate(x: float, lo: float, hi: float) -> float:
    return float(np.clip(x, lo, hi))

def simulate(cal: Calibration, scenario: Scenario) -> pd.DataFrame:
    """Stochastic, annual, system-dynamics-style urban simulation.

    This is an exploratory portfolio model, not an official forecast.
    """
    rng = np.random.default_rng(scenario.seed)
    rows = []

    pop = cal.population
    emp = cal.employment
    unemployment = cal.unemployment_rate
    hpi = cal.hpi

    # Indexed subsystems begin at 100 in the base year.
    housing_supply = 100.0
    service_capacity = 100.0
    infrastructure_capacity = 100.0
    fiscal_capacity = 100.0

    base_pop = cal.population
    base_emp = cal.employment

    macro = 0.0
    prior_housing_pressure = 0.0
    prev_pop_g = cal.pop_growth
    prev_job_g = cal.job_growth

    rows.append({
        "year": scenario.start_year,
        "population": pop,
        "employment": emp,
        "unemployment_rate": unemployment,
        "house_price_index": hpi,
        "housing_supply_index": housing_supply,
        "service_capacity_index": service_capacity,
        "infrastructure_capacity_index": infrastructure_capacity,
        "fiscal_capacity_index": fiscal_capacity,
        "housing_pressure": 0.0,
        "service_gap": 0.0,
        "infrastructure_gap": 0.0,
        "fiscal_gap": 0.0,
        "structural_mismatch": 0.0,
        "system_stress": 0.0,
        "threshold_crossed": False,
        "population_growth": 0.0,
        "employment_growth": 0.0,
    })

    for step in range(1, scenario.years + 1):
        year = scenario.start_year + step

        macro = (
            scenario.macro_persistence * macro
            + rng.normal(0, cal.job_volatility * scenario.volatility_scale)
        )

        job_g = (
            cal.job_growth
            + scenario.job_growth_shift
            + 0.55 * macro
            + rng.normal(0, cal.job_volatility * 0.25 * scenario.volatility_scale)
        )
        job_g = _clip_rate(job_g, -0.06, 0.07)

        pop_g = (
            cal.pop_growth
            + scenario.migration_shift
            + scenario.pop_job_elasticity * (job_g - cal.job_growth)
            - scenario.housing_cost_penalty * max(prior_housing_pressure, 0)
            + rng.normal(0, cal.pop_volatility * scenario.volatility_scale)
        )
        pop_g = _clip_rate(pop_g, -0.04, 0.04)

        emp *= (1 + job_g)
        pop *= (1 + pop_g)

        # Approximate unemployment response to relative labor demand/population growth.
        unemployment += -12.0 * (job_g - pop_g) + rng.normal(0, 0.20 * scenario.volatility_scale)
        unemployment = float(np.clip(unemployment, 1.5, 14.0))

        pop_index = 100 * pop / base_pop
        emp_index = 100 * emp / base_emp

        housing_demand = 0.75 * pop_index + 0.25 * emp_index
        supply_g = (
            scenario.housing_supply_growth
            + scenario.housing_response * max(pop_g - scenario.housing_supply_growth, -0.004)
            + rng.normal(0, 0.0020 * scenario.volatility_scale)
        )
        supply_g = _clip_rate(supply_g, -0.015, 0.04)
        housing_supply *= (1 + supply_g)

        housing_pressure = housing_demand / housing_supply - 1.0
        prior_housing_pressure = housing_pressure

        hpi_g = (
            0.025
            + scenario.housing_price_elasticity * housing_pressure
            + 0.10 * job_g
            + rng.normal(0, 0.012 * scenario.volatility_scale)
        )
        hpi_g = _clip_rate(hpi_g, -0.12, 0.18)
        hpi *= (1 + hpi_g)

        # Services and infrastructure respond more slowly than demand.
        service_demand = 0.70 * pop_index + 0.30 * emp_index
        service_capacity *= (1 + _clip_rate(
            scenario.service_capacity_growth
            + 0.10 * max((fiscal_capacity/100) - 1, -0.10),
            -0.02, 0.04
        ))

        infrastructure_demand = 0.55 * pop_index + 0.45 * emp_index
        infrastructure_capacity *= (1 + _clip_rate(
            scenario.infrastructure_growth, -0.02, 0.04
        ))

        fiscal_g = (
            0.45 * job_g
            + 0.30 * pop_g
            - 0.0015 * max(unemployment - cal.unemployment_rate, 0)
            + rng.normal(0, 0.0025 * scenario.volatility_scale)
        )
        fiscal_capacity *= (1 + _clip_rate(fiscal_g, -0.05, 0.05))
        fiscal_demand = 0.60 * pop_index + 0.40 * emp_index

        service_gap = max(service_demand / service_capacity - 1.0, 0.0)
        infrastructure_gap = max(infrastructure_demand / infrastructure_capacity - 1.0, 0.0)
        fiscal_gap = max(fiscal_demand / fiscal_capacity - 1.0, 0.0)

        # Normalize multiple subsystems into a transparent stress score.
        u_stress = np.clip((unemployment - 2.5) / 7.5, 0, 1)
        h_stress = np.clip(max(housing_pressure, 0) / 0.15, 0, 1)
        s_stress = np.clip(service_gap / 0.15, 0, 1)
        i_stress = np.clip(infrastructure_gap / 0.15, 0, 1)
        f_stress = np.clip(fiscal_gap / 0.12, 0, 1)

        mismatch = float(np.mean([h_stress, s_stress, i_stress, f_stress]))
        stress = float(
            0.18 * u_stress
            + 0.22 * h_stress
            + 0.22 * s_stress
            + 0.22 * i_stress
            + 0.16 * f_stress
        )

        rows.append({
            "year": year,
            "population": pop,
            "employment": emp,
            "unemployment_rate": unemployment,
            "house_price_index": hpi,
            "housing_supply_index": housing_supply,
            "service_capacity_index": service_capacity,
            "infrastructure_capacity_index": infrastructure_capacity,
            "fiscal_capacity_index": fiscal_capacity,
            "housing_pressure": housing_pressure,
            "service_gap": service_gap,
            "infrastructure_gap": infrastructure_gap,
            "fiscal_gap": fiscal_gap,
            "structural_mismatch": mismatch,
            "system_stress": stress,
            "threshold_crossed": stress >= scenario.stress_threshold,
            "population_growth": pop_g,
            "employment_growth": job_g,
        })

        prev_pop_g = pop_g
        prev_job_g = job_g

    out = pd.DataFrame(rows)
    out["state"] = pd.cut(
        out["system_stress"],
        bins=[-np.inf, 0.30, 0.50, 0.70, np.inf],
        labels=["stable", "watch", "stressed", "critical"]
    ).astype(str)
    return out

def first_threshold_year(sim: pd.DataFrame) -> float:
    hit = sim.loc[sim["threshold_crossed"], "year"]
    return float(hit.iloc[0]) if len(hit) else np.nan

def run_monte_carlo(
    cal: Calibration,
    scenario: Scenario,
    n: int = 500,
    seed: int = 123
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return long trajectories and yearly quantile summary."""
    master = np.random.default_rng(seed)
    frames = []
    for run_id in range(n):
        sc = replace(
            scenario,
            seed=int(master.integers(0, 2_000_000_000)),
            migration_shift=scenario.migration_shift + master.normal(0, 0.0020),
            job_growth_shift=scenario.job_growth_shift + master.normal(0, 0.0030),
            housing_supply_growth=max(-0.005, scenario.housing_supply_growth + master.normal(0, 0.0025)),
            service_capacity_growth=max(-0.005, scenario.service_capacity_growth + master.normal(0, 0.0025)),
            infrastructure_growth=max(-0.005, scenario.infrastructure_growth + master.normal(0, 0.0025)),
        )
        sim = simulate(cal, sc)
        sim["run_id"] = run_id
        frames.append(sim)

    long = pd.concat(frames, ignore_index=True)
    summary = (
        long.groupby("year")
        .agg(
            population_p10=("population", lambda s: s.quantile(0.10)),
            population_p50=("population", "median"),
            population_p90=("population", lambda s: s.quantile(0.90)),
            stress_p10=("system_stress", lambda s: s.quantile(0.10)),
            stress_p50=("system_stress", "median"),
            stress_p90=("system_stress", lambda s: s.quantile(0.90)),
            threshold_probability=("threshold_crossed", "mean"),
        )
        .reset_index()
    )
    return long, summary
