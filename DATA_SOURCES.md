# Data Sources — Flagship Version

## Census geography
**U.S. Census Bureau, 2024 TIGER/Line Census Tracts — Alabama**  
`https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_01_tract.zip`

The pipeline filters Alabama tracts to Bibb (007), Blount (009), Chilton (021), Jefferson (073), St. Clair (115), Shelby (117), and Walker (127) counties.

## ACS tract context
The pipeline requests 2024 ACS 5-year tract estimates through the Census Reporter API (`acs2024_5yr`). Census Reporter provides a programmatic presentation of Census ACS data. Variables used include total population, median household income, housing units, occupancy/vacancy, tenure, median gross rent, median home value, and commuting mode.

For official ACS documentation and variable definitions, use the U.S. Census Bureau 2024 ACS 5-year developer documentation.

## Transit
**Birmingham-Jefferson County Transit Authority (MAX), static GTFS.** The pipeline first attempts the current publisher feed and validates the required files. If that feed is incomplete/unavailable, it falls back to the archived 2024 publisher feed that Transitland successfully imported.

## Housing / development
- FRED `ATNHPIUS13820Q` — FHFA All-Transactions House Price Index for Birmingham-Hoover.
- FRED `BIRM801BPPRIVSA` — private housing units authorized by building permits in the Birmingham-Hoover area.

## Baseline population and labor market
- FRED `BIRPOP` — resident population.
- FRED `LAUMT011382000000005A` — employed persons.
- FRED `LAUMT011382000000003A` — unemployment rate.

Underlying agencies include the U.S. Census Bureau, U.S. Bureau of Labor Statistics, and Federal Housing Finance Agency.
