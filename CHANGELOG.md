# CHANGELOG

## Unreleased

- Allow users to save the GreenHEARTOutput class as a yaml file and read that yaml to an instance of the output class
- Remove reference_plants from examples. Reference plants can now be found in the [ReferenceHybridSystemDesigns](https://github.com/NREL/ReferenceHybridSystemDesigns) repository.

## v0.1.4 [4 February 2025]

- Adds `CoolProp` to `pyproject.toml`
- Changes units of `lcoe_real` in `HOPPComponent` from "MW*h" to "kW*h"
- Adds `pre-commit`, `ruff`, and `isort` checks, and CI workflow to ensure these steps aren't
  skipped.
- Updates steel cost year to 2022
- Updates ammonia cost year to 2022
- Requires HOPP 3.1.1 or higher
- Updates tests to be compatible with HOPP 3.1.1 with ProFAST integration
- Removes support for python 3.9
- Add steel feedstock transport costs (lime, carbon, and iron ore pellets)
- Allow individual debt rate, equity rate, and debt/equity ratio/split for each subsystem
- Add initial docs focused on new GreenHEART development
- New documentation CI pipeline to publish documentation at nrel.github.io/GreenHEART/ and test
  that the documentation site will build on each pull request.
- Placeholder documentation content has been removed from the site build

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
