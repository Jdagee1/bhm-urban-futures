from pathlib import Path
import zipfile
import pandas as pd

from src.accessibility import validate_gtfs_zip, weekday_stop_service


def _write_gtfs(path: Path):
    files = {
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nS1,One,33.5,-86.8\nS2,Two,33.6,-86.7\n",
        "trips.txt": "route_id,service_id,trip_id\nR1,WD,T1\nR1,WE,T2\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,08:00:00,08:00:00,S1,1\nT1,08:10:00,08:10:00,S2,2\nT2,09:00:00,09:00:00,S1,1\n",
        "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nWD,1,1,1,1,1,0,0,20260101,20261231\nWE,0,0,0,0,0,1,1,20260101,20261231\n",
    }
    with zipfile.ZipFile(path, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)


def test_weekday_departures(tmp_path):
    p = tmp_path / "gtfs.zip"
    _write_gtfs(p)
    ok, missing = validate_gtfs_zip(p)
    assert ok and not missing
    out = weekday_stop_service(p, "wednesday")
    d = dict(zip(out.stop_id, out.weekday_departures))
    assert d == {"S1": 1, "S2": 1}
