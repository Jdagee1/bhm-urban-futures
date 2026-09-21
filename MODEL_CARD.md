# Model Card — BHM Urban Futures Flagship

## Purpose
Portfolio-grade computational urban analysis for the Birmingham–Hoover metropolitan area. The model is designed to explore coupled urban change, forecast uncertainty, spatial redistribution, vulnerability conditions, and potential early-warning thresholds.

## Intended users
Analysts, planners, researchers, nonprofit/public-interest teams, and hiring managers evaluating the portfolio project.

## Not an official forecast
Outputs are conditional simulations. They should not be used directly for budgeting, zoning, infrastructure commitments, investment decisions, emergency management, or resource-allocation decisions.

## Geographic scope
Birmingham–Hoover metropolitan area, with optional tract-level geography for Bibb, Blount, Chilton, Jefferson, St. Clair, Shelby, and Walker counties.

## Observed inputs
- metro population history;
- metro employment history;
- metro unemployment history;
- recent county population history;
- optional Census tract geometry;
- optional ACS tract demographics/housing context;
- optional MAX Transit GTFS;
- optional FHFA HPI and building-permit series.

## Stylized relationships
The model currently uses transparent assumptions for:
- cross-system feedback coefficients;
- public-service capacity;
- infrastructure capacity;
- fiscal capacity;
- composite structural mismatch;
- composite system stress;
- tract redistribution / growth-capacity weighting.

These are exposed precisely because the portfolio should demonstrate sensitivity analysis and model-risk awareness rather than present assumptions as facts.

## Uncertainty
The project includes stochastic annual shocks, parameter variation, Monte Carlo simulation, configurable thresholds, and scenario discovery.

## Spatial model caveat
Tract redistribution is constrained to the simulated metro total and uses a transparent scenario score. It is a spatial experiment, not a neighborhood-level official forecast and not a measure of neighborhood worth or desirability.

## Validation roadmap
1. rolling-origin historical backtests;
2. subsystem-specific empirical calibration;
3. tract/county holdout validation;
4. parameter identifiability analysis;
5. comparison with independent population and development forecasts;
6. uncertainty calibration / coverage testing;
7. expert review of threshold definitions;
8. documented data-vintage and geography changes.
