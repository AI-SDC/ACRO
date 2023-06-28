# Changelog

## Development

Changes:
*

## Version 0.2.0 (Jun 28, 2023)

Changes:
*    Serialize JSON output field as a dictionary instead of string.
*    Major code refactor.
*    Add status, type and properties to the output metadata.
*    Remove the timestamp from the output naming.
*    Remove automatic reloading of existing results.
*    Make custom file paths relatve instead of absolute.
*    Split statsmodels outputs into multiple csv files instead of one.
*    Change output field in JSON is to a list of file paths.
*    Finalise() now takes two arguments: path and ext to specify a folder.
*    Automatically copy custom outputs to the outputs folder upon finalise.
*    Fix a bug attempting to write custom outputs in excel.
*    ISO format timestamps.
*    Store comments as a list of strings.

## Version 0.1.0 (Apr 28, 2023)

Changes:
*    Handle missing values.
*    Update the output from the regression to have new line between each output in the csv files.
*    Fix several minor bugs.

## Version 0.0.6 (Apr 16, 2023)

Changes:
*    Separate analytic results out from json files.
*    Add timestamps to the output names and append the new outputs to the existing json file.
*    Create functionality for users to rename outputs.
*    Create functionality to add comments to outputs.
*    Create functionality to add currently unsupported outputs to the list of outputs.

## Version 0.0.5 (Nov 02, 2022)

Changes:
*    Package for PyPI.
*    Clean tests.

## Version 0.0.4 (Oct 14, 2022)

Changes:
*    Fix complex table checking.

## Version 0.0.3 (Oct 14, 2022)

Initial alpha.
