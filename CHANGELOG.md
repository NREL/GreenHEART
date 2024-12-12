# CHANGELOG

## Unreleased

- add `CoolProp` to `pyproject.toml`
- change units of `lcoe_real` in `HOPPComponent` from "MW*h" to "kW*h"
- Adds `pre-commit`, `ruff`, and `isort` checks, and CI workflow to ensure these steps aren't
  skipped.

## v0.1.3 [1 November 2024]

- Replaces the git ProFAST installation with a PyPI installation.
- Removed dependence on external electrolyzer repo
- Updated CI to use conda environments with reproducible environment artifacts
- Rename logger from "wisdem/weis" to "greenheart"
- Remove unsupported optimization algorithms

## v0.1.2 [28 October 2024]

- Minor updates to examples for NAWEA workshop.
- Adds `environment.yml` for easy environment creation and GreenHEART installation.

## v0.1.1 [22 October 2024]

- ?

## v0.1 [16 October 2024]

- Project has been separated from HOPP and moved into GreenHEART, removing all HOPP infrastructure.
