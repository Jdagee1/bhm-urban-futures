
from pathlib import Path
import pandas as pd

FRED_SERIES = {
    "BIRPOP": "Resident population, Birmingham-Hoover MSA",
    "LAUMT011382000000005A": "Employed persons, annual",
    "LAUMT011382000000003A": "Unemployment rate, annual",
    "ATNHPIUS13820Q": "FHFA all-transactions house price index, quarterly",
    "BIRM801BPPRIVSA": "Housing units authorized by building permits, monthly SA",
    "ALBIBB7POP": "Bibb County population",
    "ALBLOU9POP": "Blount County population",
    "ALCHIL1POP": "Chilton County population",
    "ALJEFF5POP": "Jefferson County population",
    "ALSHEL0POP": "Shelby County population",
    "ALSTCL5POP": "St. Clair County population",
    "ALWALK5POP": "Walker County population",
}

def fetch_series(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    df = pd.read_csv(url)
    df.columns = ["date", series_id]
    return df

def main():
    out = Path(__file__).resolve().parents[1] / "data" / "fred_live"
    out.mkdir(parents=True, exist_ok=True)
    for sid, label in FRED_SERIES.items():
        print(f"Fetching {sid}: {label}")
        fetch_series(sid).to_csv(out / f"{sid}.csv", index=False)

if __name__ == "__main__":
    main()
