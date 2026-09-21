from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

ALABAMA_TRACTS_URL = "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_01_tract.zip"
GTFS_CANDIDATES = [
    "https://maxtransit.org/GTFS/2026/google_transit_Working.zip",
    "https://maxtransit.org/wp-content/uploads/2024/09/google_transit_Working.zip",
]
FRED = {
    "hpi": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=ATNHPIUS13820Q",
    "permits": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BIRM801BPPRIVSA",
}
COUNTY_FIPS = {
    "007": "Bibb",
    "009": "Blount",
    "021": "Chilton",
    "073": "Jefferson",
    "115": "St. Clair",
    "117": "Shelby",
    "127": "Walker",
}
CR_RELEASE = "acs2024_5yr"
CR_TABLES = ["B01003","B19013","B25001","B25002","B25003","B25064","B25077","B08301"]


def download(url: str, path: Path, timeout: int = 90) -> Path:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "BHM-Urban-Futures/1.0"})
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def fetch_censusreporter_county(county_fips: str) -> dict:
    parent = f"05000US01{county_fips}"
    url = f"https://api.censusreporter.org/1.0/data/show/{CR_RELEASE}"
    params = {
        "table_ids": ",".join(CR_TABLES),
        "geo_ids": f"140|{parent}",
    }
    r = requests.get(url, params=params, timeout=120, headers={"User-Agent": "BHM-Urban-Futures/1.0"})
    r.raise_for_status()
    return r.json()


def _estimate(table_data: dict, key: str):
    try:
        return table_data["estimate"].get(key)
    except Exception:
        return None


def parse_censusreporter(payloads: list[dict]) -> pd.DataFrame:
    rows = []
    for payload in payloads:
        for geoid, tables in payload.get("data", {}).items():
            if not geoid.startswith("14000US"):
                continue
            rows.append({
                "GEOID": geoid.replace("14000US", ""),
                "population": _estimate(tables.get("B01003", {}), "B01003001"),
                "median_household_income": _estimate(tables.get("B19013", {}), "B19013001"),
                "housing_units": _estimate(tables.get("B25001", {}), "B25001001"),
                "occupied_units": _estimate(tables.get("B25002", {}), "B25002002"),
                "vacant_units": _estimate(tables.get("B25002", {}), "B25002003"),
                "owner_occupied": _estimate(tables.get("B25003", {}), "B25003002"),
                "renter_occupied": _estimate(tables.get("B25003", {}), "B25003003"),
                "median_gross_rent": _estimate(tables.get("B25064", {}), "B25064001"),
                "median_home_value": _estimate(tables.get("B25077", {}), "B25077001"),
                "commuters_total": _estimate(tables.get("B08301", {}), "B08301001"),
                "commuters_public_transit": _estimate(tables.get("B08301", {}), "B08301010"),
            })
    df = pd.DataFrame(rows)
    for c in df.columns:
        if c != "GEOID":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def prepare_tracts():
    import geopandas as gpd
    from src.accessibility import weekday_stop_service, aggregate_stops_to_tracts, validate_gtfs_zip

    tiger_zip = RAW / "tl_2024_01_tract.zip"
    if not tiger_zip.exists():
        print("Downloading 2024 Alabama TIGER/Line tracts...")
        download(ALABAMA_TRACTS_URL, tiger_zip)

    tracts = gpd.read_file(f"zip://{tiger_zip}")
    tracts = tracts[tracts["COUNTYFP"].isin(COUNTY_FIPS)].copy()
    tracts = tracts[["GEOID","COUNTYFP","NAMELSAD","ALAND","AWATER","geometry"]]
    tracts["county"] = tracts["COUNTYFP"].map(COUNTY_FIPS)

    payloads = []
    for fips, name in COUNTY_FIPS.items():
        print(f"Fetching ACS for {name} County...")
        payloads.append(fetch_censusreporter_county(fips))
    acs = parse_censusreporter(payloads)
    tracts = tracts.merge(acs, on="GEOID", how="left")

    gtfs_path = RAW / "max_transit_gtfs.zip"
    if not gtfs_path.exists():
        last_error = None
        for url in GTFS_CANDIDATES:
            try:
                temp = RAW / "_gtfs_candidate.zip"
                download(url, temp)
                ok, missing = validate_gtfs_zip(temp)
                if ok:
                    temp.replace(gtfs_path)
                    print(f"Using GTFS: {url}")
                    break
                last_error = RuntimeError(f"GTFS missing {missing}: {url}")
                temp.unlink(missing_ok=True)
            except Exception as e:
                last_error = e
        if not gtfs_path.exists():
            raise RuntimeError(f"No valid GTFS candidate could be downloaded: {last_error}")

    stops = weekday_stop_service(gtfs_path, weekday="wednesday")
    transit = aggregate_stops_to_tracts(stops, tracts)
    tracts = tracts.merge(transit, on="GEOID", how="left")
    tracts["transit_stops"] = tracts["transit_stops"].fillna(0).astype(int)
    tracts["weekday_departures"] = tracts["weekday_departures"].fillna(0).astype(int)

    tracts.to_file(PROCESSED / "birmingham_msa_tract_context.geojson", driver="GeoJSON")
    tracts.drop(columns="geometry").to_csv(PROCESSED / "birmingham_msa_tract_metrics.csv", index=False)

    for name, url in FRED.items():
        print(f"Fetching FRED {name}...")
        download(url, RAW / f"fred_{name}.csv")

    return tracts


def main():
    tracts = prepare_tracts()
    manifest = {
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "tracts": int(len(tracts)),
        "counties": COUNTY_FIPS,
        "sources": {
            "tiger_tracts": ALABAMA_TRACTS_URL,
            "census_reporter_release": CR_RELEASE,
            "census_reporter_note": "Census Reporter serves ACS estimates; see project DATA_SOURCES.md for Census source documentation.",
            "gtfs_candidates": GTFS_CANDIDATES,
            "fred": FRED,
        },
    }
    (PROCESSED / "source_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
