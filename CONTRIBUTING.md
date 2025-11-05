# Contributing

Contributions to this repository are very welcome. Please create an issue before starting any significant work so that we can discuss and understand the changes. If you are interested in contributing, feel free to contact us or create an issue in the [issue tracking system](https://github.com/AI-SDC/ACRO/issues). Alternatively, you may [fork](https://docs.github.com/en/github/getting-started-with-github/fork-a-repo) the project and submit a [pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork). All contributions must be made under the same license as the rest of the project: [MIT License](../blob/main/LICENSE). New code should be accompanied with appropriate unit tests and documentation; a brief description of the changes made should be added to the top of `CHANGELOG.md`. If this is your first contribution to the repository, please also add your details to `CITATION.cff`. If you are introducing new imports, then these must also be added to `requirements.txt` (in root and docs folders) and `setup.py`. After creating a pull request, the continuous integration tools will automatically run the unit tests, apply the pre-commit checks listed below, and build and deploy the Sphinx documentation (when merged into the main branch.)

## Pull Request Standards

All pull requests must meet the following requirements before being accepted:

- **All pre-commit checks pass** (includes Ruff formatting and linting)
- **Codecov reports at least 99% statement coverage**
- **Tests do more than just make sure the lines run, they actually check for desired effects**

## Development

Clone the repository and install the dependencies (within a virtual environment):

```
$ git clone git@github.com:AI-SDC/ACRO.git
$ cd ACRO
$ pip install -e .
```

Then to run the tests:

```
$ pip install pytest
$ pytest .
```

## Directory Structure

* `acro`: contains ACRO source code.
* `data`:  contains data files for testing.
* `docs`: contains [Sphinx](https://www.sphinx-doc.org) documentation.
* `notebooks`: contains example notebooks.
* `stata`: contains Stata wrapper code.
* `test`: contains unit tests.

## Style Guide

Code quality is maintained through [pre-commit](https://pre-commit.com) hooks that run [Ruff](https://github.com/astral-sh/ruff) (which includes pylint-style checks) along with other formatting and linting tools.

A [pre-commit](https://pre-commit.com) configuration [file](../tree/main/.pre-commit-config.yaml) is provided to automatically:
* Trim trailing whitespace and fix line endings;
* Check for spelling errors;
* Check Yaml files;
* Automatically format and lint with [Ruff](https://github.com/astral-sh/ruff);

Pre-commit can be setup locally as follows:

```
$ pip install pre-commit
```

Then to run on all files locally:

```
$ pre-commit run -a
```

Make any corrections as necessary and re-run before committing the fixes and then pushing.

To install as a hook that executes with every `git commit`:

```
$ pre-commit install
```
