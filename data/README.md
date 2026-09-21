# Data directory

Small historical baseline CSVs are committed so the simulator works immediately.

Large / externally refreshed spatial data are **not** committed. Run:

```bash
python scripts/prepare_flagship_data.py
```

That pipeline downloads and prepares:

- 2024 Alabama Census TIGER/Line tract geometry, filtered to the seven Birmingham–Hoover MSA counties;
- ACS 2024 5-year tract estimates via Census Reporter for population, income, housing, rent/home value, tenure, and public-transit commuting;
- MAX Transit static GTFS, with validation and a known-good archived-feed fallback;
- FHFA house-price index and Census building-permit series through FRED.

Prepared outputs are written to `data/processed/`.
