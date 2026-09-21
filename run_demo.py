from pathlib import Path
import pandas as pd

from src.model import load_history, calibrate, Scenario, simulate
from src.spatial import load_county_history, allocate_metro_population
from src.discovery import generate_experiments, fit_vulnerability_model
from src.spatial_simulation import simulate_tract_redistribution

ROOT = Path(__file__).resolve().parent
history = load_history(ROOT / "data" / "birmingham_msa_history.csv")
county_history = load_county_history(ROOT / "data" / "msa_county_population_2021_2025.csv")
cal = calibrate(history)
scenario = Scenario(years=20, seed=42)
sim = simulate(cal, scenario)

print("Calibration:", cal)
print("\nMetro scenario tail:")
print(sim[["year","population","employment","system_stress","state"]].tail())

county = allocate_metro_population(sim, county_history, seed=42)
print("\nCounty allocation at forecast end:")
print(county[county["year"] == county["year"].max()].sort_values("population", ascending=False))

tract_path = ROOT / "data" / "processed" / "birmingham_msa_tract_metrics.csv"
if tract_path.exists():
    tracts = pd.read_csv(tract_path, dtype={"GEOID": str, "COUNTYFP": str})
    ts = simulate_tract_redistribution(sim, tracts, seed=42)
    print("\nTop simulated tract populations at forecast end:")
    print(ts[ts["year"] == ts["year"].max()].nlargest(10, "population"))
else:
    print("\nSpatial tract data not prepared. Run: python scripts/prepare_flagship_data.py")

experiments = generate_experiments(cal, scenario, n=250, seed=99)
_, importance = fit_vulnerability_model(experiments, seed=99)
print("\nScenario-discovery importance:")
print(importance)
