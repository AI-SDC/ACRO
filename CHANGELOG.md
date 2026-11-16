# Changelog

## Version 1.1.0 (Nov 05, 2026)

### Additional Functionality

* Add command shortcuts and factor notation in Stata. ([#423](https://github.com/AI-SDC/ACRO/pull/423), [#427](https://github.com/AI-SDC/ACRO/pull/427))
* Add Cox proportional hazards regression support in Python and Stata. ([#419](https://github.com/AI-SDC/ACRO/pull/419), [#422](https://github.com/AI-SDC/ACRO/pull/422))
* Add disclosure risk explanations. ([#428](https://github.com/AI-SDC/ACRO/pull/428))

### Chore

* Bump the version number to 1.1.0. ([#430](https://github.com/AI-SDC/ACRO/pull/430))

### Fix

* Correct the MyBinder link. ([#417](https://github.com/AI-SDC/ACRO/pull/417))
* Include custom outputs in XLSX finalisation. ([#418](https://github.com/AI-SDC/ACRO/pull/418))
* Join index conditions with `&` to avoid `TypeError`. ([#415](https://github.com/AI-SDC/ACRO/pull/415))

## Version 1.0.1 (Aug 10, 2026)

### Additional Functionality

* Add pie chart support. ([#355](https://github.com/AI-SDC/ACRO/pull/355))
* Add rounding as a protection mechanism. ([#381](https://github.com/AI-SDC/ACRO/pull/381))
* Create and enforce a blocked file extension list for custom outputs. ([#377](https://github.com/AI-SDC/ACRO/pull/377))
* Flag histogram bin-edge disclosure risks. ([#192](https://github.com/AI-SDC/ACRO/pull/192), [#382](https://github.com/AI-SDC/ACRO/pull/382))
* Make ACRO ontology-driven. ([#395](https://github.com/AI-SDC/ACRO/pull/395))

### Chore

* Add type hints. ([#343](https://github.com/AI-SDC/ACRO/pull/343))
* Bump the version number to 1.0.1.
* Clean up notebooks and folders. ([#336](https://github.com/AI-SDC/ACRO/pull/336))
* Include the required JSON files in the `acro` package data and correct its `pyproject.toml` configuration.
* Update GitHub Actions dependencies, including `codecov/codecov-action` from version 5 to 6. ([#356](https://github.com/AI-SDC/ACRO/pull/356), [#374](https://github.com/AI-SDC/ACRO/pull/374))
* Update pre-commit hooks. ([#333](https://github.com/AI-SDC/ACRO/pull/333), [#366](https://github.com/AI-SDC/ACRO/pull/366), [#372](https://github.com/AI-SDC/ACRO/pull/372), [#375](https://github.com/AI-SDC/ACRO/pull/375), [#385](https://github.com/AI-SDC/ACRO/pull/385), [#388](https://github.com/AI-SDC/ACRO/pull/388))
* Update Ruff configuration: enable 11 additional rule sets, ignore D213 because it conflicts with D212, and remove `extend-ignore`; remove unused pylint inline pragmas. ([#371](https://github.com/AI-SDC/ACRO/pull/371), [#373](https://github.com/AI-SDC/ACRO/pull/373))

### CI

* Run tests on pull requests without running them twice. ([#368](https://github.com/AI-SDC/ACRO/pull/368))

### Documentation

* Automate changelog generation from pull request names. ([#352](https://github.com/AI-SDC/ACRO/pull/352))
* Replace pre-commit with prek in the contributing guide, update the guide, and add an AI policy. ([#338](https://github.com/AI-SDC/ACRO/pull/338), [#369](https://github.com/AI-SDC/ACRO/pull/369))
* Update documentation and simplify examples. ([#334](https://github.com/AI-SDC/ACRO/pull/334))
* Update the Stata cheat sheet. ([#354](https://github.com/AI-SDC/ACRO/pull/354))

### Fix

* Correct cell ID misalignment and hierarchical reindexing. ([#367](https://github.com/AI-SDC/ACRO/pull/367))
* Correct the README Python notebook link. ([#359](https://github.com/AI-SDC/ACRO/pull/359))
* Handle invalid aggregation functions in Stata. ([#365](https://github.com/AI-SDC/ACRO/pull/365))
* Honor `zeros_are_disclosive` when checking empty histogram bins. ([#308](https://github.com/AI-SDC/ACRO/pull/308), [#386](https://github.com/AI-SDC/ACRO/pull/386))
* Resolve shape mismatches in `crosstab` and `pivot_table` with aggregation functions. ([#347](https://github.com/AI-SDC/ACRO/pull/347))

### Refactoring

* Extract the `acro_artifacts` folder name into the `ARTIFACTS_DIR` constant. ([#376](https://github.com/AI-SDC/ACRO/pull/376))
* Use dynamic column names in `rounded_survival_table`. ([#332](https://github.com/AI-SDC/ACRO/pull/332))

## Version 0.4.12 (Feb 02, 2026)

### Additional Functionality

* Add setters to toggle suppression ([#326](https://github.com/AI-SDC/ACRO/pull/326))
* Add support for `init` options in Stata ([#320](https://github.com/AI-SDC/ACRO/pull/320))
* Disallow `.gph` files as custom outputs in Stata ([#296](https://github.com/AI-SDC/ACRO/pull/296))
* Make finalise non-interactive by default ([#309](https://github.com/AI-SDC/ACRO/pull/309))

### CI

* Set `MPLBACKEND`

### Documentation

* Add documentation ([#273](https://github.com/AI-SDC/ACRO/pull/273), [#287](https://github.com/AI-SDC/ACRO/pull/287), [#288](https://github.com/AI-SDC/ACRO/pull/288), [#289](https://github.com/AI-SDC/ACRO/pull/289), [#291](https://github.com/AI-SDC/ACRO/pull/291), [#304](https://github.com/AI-SDC/ACRO/pull/304), [#306](https://github.com/AI-SDC/ACRO/pull/306), [#318](https://github.com/AI-SDC/ACRO/pull/318))

### Fix

* Handle spaces in variable names for `crosstab` ([#321](https://github.com/AI-SDC/ACRO/pull/321))
* Update summary status logic to reflect suppression state ([#317](https://github.com/AI-SDC/ACRO/pull/317))

### Testing

* Add test for `rounded_survival_table` function in survival analysis ([#324](https://github.com/AI-SDC/ACRO/pull/324))

## Version 0.4.11 (Nov 03, 2025)

### Chore

* Increase max pandas to <=2.3.3 to avoid building from source for Python 3.14 ([#282](https://github.com/AI-SDC/ACRO/pull/282))

## Version 0.4.10 (Nov 03, 2025)

### Chore

* Drop Python 3.9 and support Python 3.14 ([#280](https://github.com/AI-SDC/ACRO/pull/280))

### Fix

* Various fixes and improvements for stata ([#278](https://github.com/AI-SDC/ACRO/pull/278))

## Version 0.4.9 (Jul 02, 2025)

### Chore

* Cap `scipy<1.16.0` ([#266](https://github.com/AI-SDC/ACRO/pull/266))

### Documentation

* Update notebooks for Numpy version 2 compatibility ([#258](https://github.com/AI-SDC/ACRO/pull/258))

## Version 0.4.8 (Jan 29, 2025)

### Additional Functionality

* Add support for Numpy version 2 ([#247](https://github.com/AI-SDC/ACRO/pull/247))

## Version 0.4.7 (Oct 22, 2024)

### Additional Functionality

* Add support for Pandas version 2 ([#237](https://github.com/AI-SDC/ACRO/pull/237))

## Version 0.4.6 (Jun 25, 2024)

### Additional Functionality

* Add mode aggregation function ([#194](https://github.com/AI-SDC/ACRO/pull/194))

### Chore

* Add Ruff linting/formatting ([#210](https://github.com/AI-SDC/ACRO/pull/210), [#214](https://github.com/AI-SDC/ACRO/pull/214))
* Limit numpy dependency to less than v2.0.0 ([#220](https://github.com/AI-SDC/ACRO/pull/220))
* Remove useless pylint suppression ([#213](https://github.com/AI-SDC/ACRO/pull/213))
* Update packaging ([#209](https://github.com/AI-SDC/ACRO/pull/209))

### CI

* Update CI ([#207](https://github.com/AI-SDC/ACRO/pull/207), [#208](https://github.com/AI-SDC/ACRO/pull/208))

### Documentation

* PEP 257 docstring formatting ([#212](https://github.com/AI-SDC/ACRO/pull/212))
* Update Stata examples ([#197](https://github.com/AI-SDC/ACRO/pull/197))

### Fix

* Correct minor issues, including suppression when `margins=True`
* Fix code coverage reporting ([#215](https://github.com/AI-SDC/ACRO/pull/215))
* Improve robustness of `create_dataframe()` ([#211](https://github.com/AI-SDC/ACRO/pull/211))

## Version 0.4.5 (Nov 16, 2023)

### CI

* CI updates, version numbers

## Version 0.4.4 (Nov 15, 2023)

### Additional Functionality

* Add histogram support, including the R interface, and add survival analysis to R. ([#176](https://github.com/AI-SDC/ACRO/pull/176), [#182](https://github.com/AI-SDC/ACRO/pull/182))
* Update the finalise function by checking the provided folder name and ask for new one if it exists ([#179](https://github.com/AI-SDC/ACRO/pull/179))

### Documentation

* Add inherited members from acro_tables and acro_regression to the sphinx docs ([#177](https://github.com/AI-SDC/ACRO/pull/177))
* Create an example notebook with simple examples of acro ([#170](https://github.com/AI-SDC/ACRO/pull/170))
* Update the R help function ([#178](https://github.com/AI-SDC/ACRO/pull/178))

### Fix

* Fix the problem of shape mismatch when there are two columns and the aggfunc is count or sum ([#167](https://github.com/AI-SDC/ACRO/pull/167))
* Update table suppression when totals are true for pivot table ([#165](https://github.com/AI-SDC/ACRO/pull/165))

### Testing

* Remove all files and folders created during testing ([#168](https://github.com/AI-SDC/ACRO/pull/168))

## Version 0.4.3 (Sep 22, 2023)

### Additional Functionality

* Add a directory of outputs to an acro object and creates a results file for checking ([#130](https://github.com/AI-SDC/ACRO/pull/130))
* Add installation support for Python 3.8 and 3.9 ([#135](https://github.com/AI-SDC/ACRO/pull/135))
* Add support for survival analysis ([#145](https://github.com/AI-SDC/ACRO/pull/145))
* Adding support for table function in R ([#153](https://github.com/AI-SDC/ACRO/pull/153))
* Improve screen formatting of tables ([#139](https://github.com/AI-SDC/ACRO/pull/139))
* Integrate Stata support ([#142](https://github.com/AI-SDC/ACRO/pull/142))

### Chore

* Update pandas version dependency to 1.5 ([#150](https://github.com/AI-SDC/ACRO/pull/150))

### Fix

* Fix crosstab when index or columns is a list and there is an aggregation function ([#147](https://github.com/AI-SDC/ACRO/pull/147))
* Update table suppression when totals are true ([#160](https://github.com/AI-SDC/ACRO/pull/160))

### Refactoring

* Refactor ACRO class ([#152](https://github.com/AI-SDC/ACRO/pull/152))

## Version 0.4.2 (Jul 13, 2023)

### Additional Functionality

* Add the version number to INFO messages and use INFO for exception handling of the finalise prompt. ([#116](https://github.com/AI-SDC/ACRO/pull/116))
* Update the R wrapper. ([#116](https://github.com/AI-SDC/ACRO/pull/116))

## Version 0.4.0 (Jul 11, 2023)

### Additional Functionality

* Add explicit exception handling and finalise prompt ([#112](https://github.com/AI-SDC/ACRO/pull/112))
* Add version number to JSON and use new schema ([#114](https://github.com/AI-SDC/ACRO/pull/114))
* Add writing sha256 checksums upon finalise ([#107](https://github.com/AI-SDC/ACRO/pull/107))
* Write SDC parameters to config.json upon finalise ([#111](https://github.com/AI-SDC/ACRO/pull/111))

### Refactoring

* Refactor load_json Records class function to static load_results ([#110](https://github.com/AI-SDC/ACRO/pull/110))

## Version 0.3.0 (Jul 04, 2023)

### Additional Functionality

* Add lists of flagged table cells to properties ([#104](https://github.com/AI-SDC/ACRO/pull/104))
* Add support for multiple aggregation functions ([#99](https://github.com/AI-SDC/ACRO/pull/99))
* Change missing and negative table properties to sums ([#104](https://github.com/AI-SDC/ACRO/pull/104))
* Disable automatic table suppression by default ([#91](https://github.com/AI-SDC/ACRO/pull/91))

### Refactoring

* Minor code refactor and used mypy to fix types ([#97](https://github.com/AI-SDC/ACRO/pull/97))

## Version 0.2.0 (Jun 28, 2023)

### Additional Functionality

* Add status, type and properties to the output metadata ([#89](https://github.com/AI-SDC/ACRO/pull/89))
* Automatically copy custom outputs to the outputs folder upon finalise ([#89](https://github.com/AI-SDC/ACRO/pull/89))
* Change output field in JSON to a list of file paths ([#89](https://github.com/AI-SDC/ACRO/pull/89))
* Finalise now takes two arguments: path and ext to specify a folder ([#89](https://github.com/AI-SDC/ACRO/pull/89))
* ISO format timestamps ([#89](https://github.com/AI-SDC/ACRO/pull/89))
* Make custom file paths relative instead of absolute ([#89](https://github.com/AI-SDC/ACRO/pull/89))
* Remove automatic reloading of existing results ([#89](https://github.com/AI-SDC/ACRO/pull/89))
* Remove the timestamp from the output naming ([#89](https://github.com/AI-SDC/ACRO/pull/89))
* Serialize JSON outcome field as a dictionary instead of string ([#88](https://github.com/AI-SDC/ACRO/pull/88))
* Split statsmodels outputs into multiple csv files ([#89](https://github.com/AI-SDC/ACRO/pull/89))
* Store comments as a list of strings ([#89](https://github.com/AI-SDC/ACRO/pull/89))

### Fix

* Fix a bug attempting to write custom outputs in excel ([#89](https://github.com/AI-SDC/ACRO/pull/89))

### Refactoring

* Major code refactor of output storage ([#89](https://github.com/AI-SDC/ACRO/pull/89))

## Version 0.1.0 (Apr 28, 2023)

### Additional Functionality

* Add a new line between statsmodel tables when writing csv ([#60](https://github.com/AI-SDC/ACRO/pull/60))
* Add missing value handling ([#59](https://github.com/AI-SDC/ACRO/pull/59))

### Fix

* Fix loading existing results ([#64](https://github.com/AI-SDC/ACRO/pull/64))
* Fix problems with NaNs in masks ([#63](https://github.com/AI-SDC/ACRO/pull/63))

## Version 0.0.6 (Apr 16, 2023)

### Additional Functionality

* Add explicit stack level to warnings ([#45](https://github.com/AI-SDC/ACRO/pull/45))
* Add functionality for users to rename outputs ([#52](https://github.com/AI-SDC/ACRO/pull/52))
* Add functionality to add comments to outputs ([#54](https://github.com/AI-SDC/ACRO/pull/54))
* Add functionality to add currently unsupported outputs ([#58](https://github.com/AI-SDC/ACRO/pull/58))
* Add timestamps to the output names and append the new outputs to the existing JSON file ([#51](https://github.com/AI-SDC/ACRO/pull/51))
* Separate analytic results from JSON files ([#46](https://github.com/AI-SDC/ACRO/pull/46))

## Version 0.0.5 (Nov 02, 2022)

### Chore

* Package for PyPI

### Testing

* Clean tests

## Version 0.0.4 (Oct 14, 2022)

### Fix

* Fix complex table checking

## Version 0.0.3 (Oct 14, 2022)

### Other

* Initial alpha
