from __future__ import annotations

from io import TextIOWrapper
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd

REQUIRED_GTFS = {"stops.txt", "trips.txt", "stop_times.txt"}


def validate_gtfs_zip(path: str | Path) -> tuple[bool, list[str]]:
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
    missing = sorted(REQUIRED_GTFS - names)
    return len(missing) == 0, missing


def _read_gtfs_table(zf: zipfile.ZipFile, name: str) -> pd.DataFrame:
    with zf.open(name) as f:
        return pd.read_csv(f, dtype=str, low_memory=False)


def weekday_stop_service(path: str | Path, weekday: str = "wednesday") -> pd.DataFrame:
    """Compute scheduled weekday departures at each stop from a static GTFS feed.

    This intentionally uses calendar.txt weekday flags rather than a specific date so
    it remains reproducible across feed vintages. calendar_dates exceptions are not
    applied in this first portfolio version.
    """
    path = Path(path)
    ok, missing = validate_gtfs_zip(path)
    if not ok:
        raise ValueError(f"Invalid GTFS archive; missing: {missing}")

    weekday = weekday.lower()
    if weekday not in {"monday","tuesday","wednesday","thursday","friday","saturday","sunday"}:
        raise ValueError("weekday must be a day name")

    with zipfile.ZipFile(path) as zf:
        stops = _read_gtfs_table(zf, "stops.txt")
        trips = _read_gtfs_table(zf, "trips.txt")
        stop_times = _read_gtfs_table(zf, "stop_times.txt")

        if "calendar.txt" in zf.namelist():
            cal = _read_gtfs_table(zf, "calendar.txt")
            active_services = set(cal.loc[cal[weekday].astype(str) == "1", "service_id"].astype(str))
            if active_services:
                trips = trips[trips["service_id"].astype(str).isin(active_services)]

    trip_ids = set(trips["trip_id"].astype(str))
    st = stop_times[stop_times["trip_id"].astype(str).isin(trip_ids)].copy()
    departures = st.groupby("stop_id").size().rename("weekday_departures")

    out = stops.merge(departures, left_on="stop_id", right_index=True, how="left")
    out["weekday_departures"] = out["weekday_departures"].fillna(0).astype(int)
    out["stop_lat"] = pd.to_numeric(out["stop_lat"], errors="coerce")
    out["stop_lon"] = pd.to_numeric(out["stop_lon"], errors="coerce")
    out = out.dropna(subset=["stop_lat", "stop_lon"])
    return out[["stop_id","stop_name","stop_lat","stop_lon","weekday_departures"]]


def aggregate_stops_to_tracts(stops: pd.DataFrame, tracts):
    """Spatially join GTFS stops to a GeoDataFrame of Census tracts."""
    import geopandas as gpd

    pts = gpd.GeoDataFrame(
        stops.copy(),
        geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]),
        crs="EPSG:4326",
    )
    tracts = tracts.to_crs("EPSG:4326")
    joined = gpd.sjoin(pts, tracts[["GEOID","geometry"]], predicate="within", how="left")
    agg = (
        joined.dropna(subset=["GEOID"])
        .groupby("GEOID")
        .agg(
            transit_stops=("stop_id", "nunique"),
            weekday_departures=("weekday_departures", "sum"),
        )
        .reset_index()
    )
    return agg
