# Changelog

## Version 0.4.9 (Jul 02, 2025)

Changes:
*   Update notebooks for Numpy version 2 compatibility ([#258](https://github.com/AI-SDC/ACRO/pull/258))
*   Cap `scipy<1.16.0` ([#266](https://github.com/AI-SDC/ACRO/pull/266))

## Version 0.4.8 (Jan 29, 2025)

Changes:
*   Add support for Numpy version 2 ([#247](https://github.com/AI-SDC/ACRO/pull/247))

## Version 0.4.7 (Oct 22, 2024)

Changes:
*   Add support for Pandas version 2 ([#237](https://github.com/AI-SDC/ACRO/pull/237))

## Version 0.4.6 (Jun 25, 2024)

Changes:
*   Add mode aggregation function ([#194](https://github.com/AI-SDC/ACRO/pull/194))
*   Update Stata examples ([#197](https://github.com/AI-SDC/ACRO/pull/197))
*   Various minor bug fixes, including fixing suppression when `margins=True`
*   Update CI ([#207](https://github.com/AI-SDC/ACRO/pull/207), [#208](https://github.com/AI-SDC/ACRO/pull/208))
*   Update packaging ([#209](https://github.com/AI-SDC/ACRO/pull/209))
*   Improve robustness of `create_dataframe()` ([#211](https://github.com/AI-SDC/ACRO/pull/211))
*   Add Ruff linting/formatting ([#210](https://github.com/AI-SDC/ACRO/pull/210), [#214](https://github.com/AI-SDC/ACRO/pull/214))
*   PEP 257 docstring formatting ([#212](https://github.com/AI-SDC/ACRO/pull/212))
*   Remove useless pylint suppression ([#213](https://github.com/AI-SDC/ACRO/pull/213))
*   Fix code coverage reporting ([#215](https://github.com/AI-SDC/ACRO/pull/215))
*   Limit numpy dependency to less than v2.0.0 ([#220](https://github.com/AI-SDC/ACRO/pull/220))

## Version 0.4.5 (Nov 16, 2023)

Changes:
*   CI updates, version numbers

## Version 0.4.4 (Nov 15, 2023)

Changes:
*   Update table suppression when totals are true for pivot table ([#165](https://github.com/AI-SDC/ACRO/pull/165))
*   Fix the problem of shape mismatch when there are two columns and the aggfunc is count or sum ([#167](https://github.com/AI-SDC/ACRO/pull/167))
*   Remove all files and folders created during testing ([#168](https://github.com/AI-SDC/ACRO/pull/168))
*   Create an example notebook with simple examples of acro ([#170](https://github.com/AI-SDC/ACRO/pull/170))
*   Add support for histogram ([#176](https://github.com/AI-SDC/ACRO/pull/176))
*   Add inherited members from acro_tables and acro_regression to the sphinx docs ([#177](https://github.com/AI-SDC/ACRO/pull/177))
*   Update the R help function ([#178](https://github.com/AI-SDC/ACRO/pull/178))
*   Update the finalise function by checking the provided folder name and ask for new one if it exists ([#179](https://github.com/AI-SDC/ACRO/pull/179))
*   Add histogram and survival analysis to R ([#182](https://github.com/AI-SDC/ACRO/pull/182))

## Version 0.4.3 (Sep 22, 2023)

Changes:
*   Add installation support for Python 3.8 and 3.9 ([#135](https://github.com/AI-SDC/ACRO/pull/135))
*   Add a directory of outputs to an acro object and creates a results file for checking ([#130](https://github.com/AI-SDC/ACRO/pull/130))
*   Improve screen formatting of tables ([#139](https://github.com/AI-SDC/ACRO/pull/139))
*   Integrate Stata support ([#142](https://github.com/AI-SDC/ACRO/pull/142))
*   Fix crosstab when index or columns is a list and there is an aggregation function ([#147](https://github.com/AI-SDC/ACRO/pull/147))
*   Add support for survival analysis ([#145](https://github.com/AI-SDC/ACRO/pull/145))
*   Update pandas version dependency to 1.5 ([#150](https://github.com/AI-SDC/ACRO/pull/150))
*   Refactor ACRO class ([#152](https://github.com/AI-SDC/ACRO/pull/152))
*   Adding support for table function in R ([#153](https://github.com/AI-SDC/ACRO/pull/153))
*   Update table suppression when totals are true ([#160](https://github.com/AI-SDC/ACRO/pull/160))

## Version 0.4.2 (Jul 13, 2023)

Changes:
*   Use INFO for exception handling finalise prompt ([#116](https://github.com/AI-SDC/ACRO/pull/116))
*   Add version number to INFO ([#116](https://github.com/AI-SDC/ACRO/pull/116))
*   Update R wrapper ([#116](https://github.com/AI-SDC/ACRO/pull/116))

## Version 0.4.0 (Jul 11, 2023)

Changes:
*    Add writing sha256 checksums upon finalise ([#107](https://github.com/AI-SDC/ACRO/pull/107))
*    Refactor load_json Records class function to static load_results ([#110](https://github.com/AI-SDC/ACRO/pull/110))
*    Write SDC parameters to config.json upon finalise ([#111](https://github.com/AI-SDC/ACRO/pull/111))
*    Add explicit exception handling and finalise prompt ([#112](https://github.com/AI-SDC/ACRO/pull/112))
*    Add version number to JSON and use new schema ([#114](https://github.com/AI-SDC/ACRO/pull/114))

## Version 0.3.0 (Jul 04, 2023)

Changes:
*    Disable automatic table suppression by default ([#91](https://github.com/AI-SDC/ACRO/pull/91))
*    Add support for multiple aggregation functions ([#99](https://github.com/AI-SDC/ACRO/pull/99))
*    Minor code refactor and used mypy to fix types ([#97](https://github.com/AI-SDC/ACRO/pull/97))
*    Add lists of flagged table cells to properties ([#104](https://github.com/AI-SDC/ACRO/pull/104))
*    Change missing and negative table properties to sums ([#104](https://github.com/AI-SDC/ACRO/pull/104))

## Version 0.2.0 (Jun 28, 2023)

Changes:
*    Serialize JSON outcome field as a dictionary instead of string ([#88](https://github.com/AI-SDC/ACRO/pull/88))
*    Major code refactor of output storage ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Add status, type and properties to the output metadata ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Remove the timestamp from the output naming ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Remove automatic reloading of existing results ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Make custom file paths relatve instead of absolute ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Split statsmodels outputs into multiple csv files ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Change output field in JSON to a list of file paths ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Finalise now takes two arguments: path and ext to specify a folder ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Automatically copy custom outputs to the outputs folder upon finalise ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Fix a bug attempting to write custom outputs in excel ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    ISO format timestamps ([#89](https://github.com/AI-SDC/ACRO/pull/89))
*    Store comments as a list of strings ([#89](https://github.com/AI-SDC/ACRO/pull/89))

## Version 0.1.0 (Apr 28, 2023)

Changes:
*    Add missing value handling ([#59](https://github.com/AI-SDC/ACRO/pull/59))
*    Add a new line between statsmodel tables when writing csv ([#60](https://github.com/AI-SDC/ACRO/pull/60))
*    Fix problems with NaNs in masks ([#63](https://github.com/AI-SDC/ACRO/pull/63))
*    Fix loading existing results ([#64](https://github.com/AI-SDC/ACRO/pull/64))

## Version 0.0.6 (Apr 16, 2023)

Changes:
*    Add explicit stack level to warnings ([#45](https://github.com/AI-SDC/ACRO/pull/45))
*    Separate analytic results from JSON files ([#46](https://github.com/AI-SDC/ACRO/pull/46))
*    Add timestamps to the output names and append the new outputs to the existing JSON file ([#51](https://github.com/AI-SDC/ACRO/pull/51))
*    Add functionality for users to rename outputs ([#52](https://github.com/AI-SDC/ACRO/pull/52))
*    Add functionality to add comments to outputs ([#54](https://github.com/AI-SDC/ACRO/pull/54))
*    Add functionality to add currently unsupported outputs ([#58](https://github.com/AI-SDC/ACRO/pull/58))

## Version 0.0.5 (Nov 02, 2022)

Changes:
*    Package for PyPI
*    Clean tests

## Version 0.0.4 (Oct 14, 2022)

Changes:
*    Fix complex table checking

## Version 0.0.3 (Oct 14, 2022)

Initial alpha
