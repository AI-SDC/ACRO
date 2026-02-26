# Contributing

Contributions to this repository are very welcome. Please create an issue before starting any significant work so that we can discuss and understand the changes. If you are interested in contributing, feel free to contact us or create an issue in the [issue tracking system](https://github.com/AI-SDC/ACRO/issues). Alternatively, you may [fork](https://docs.github.com/en/github/getting-started-with-github/fork-a-repo) the project and submit a [pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork). All contributions must be made under the same license as the rest of the project: [MIT License](../blob/main/LICENSE). New code should be accompanied with appropriate unit tests and documentation; a brief description of the changes made should be added to the top of `CHANGELOG.md`. If this is your first contribution to the repository, please also add your details to `CITATION.cff`. If you are introducing new imports, then these must also be added to `requirements.txt` (in root and docs folders) and `setup.py`. After creating a pull request, the continuous integration tools will automatically run the unit tests, apply the pre-commit checks listed below, and build and deploy the Sphinx documentation (when merged into the main branch.)

## Pull Request Standards

All pull requests must meet the following requirements before being accepted:

- **All prek checks pass** (includes Ruff formatting and linting)
- **Codecov reports at least 99% statement coverage**
- **Tests do more than just make sure the lines run, they actually check for desired effects**

## Development

Clone the repository and install the dependencies (within a virtual environment):

```shell
$ git clone git@github.com:AI-SDC/ACRO.git
$ cd ACRO
$ pip install -e .
```

Then to run the tests:

```shell
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

Code quality is maintained through [prek](https://prek.j178.dev) hooks that run [Ruff](https://github.com/astral-sh/ruff) (which includes pylint-style checks) along with other formatting and linting tools.

A [prek](https://prek.j178.dev) configuration [file](../tree/main/.pre-commit-config.yaml) is provided to automatically:
* Trim trailing whitespace and fix line endings;
* Check for spelling errors;
* Check Yaml files;
* Automatically format and lint with [Ruff](https://github.com/astral-sh/ruff);

Prek can be setup locally as follows:

```shell
$ pip install prek
```

Then to run on all files locally:

```shell
$ prek run -a
```

Make any corrections as necessary and re-run before committing the fixes and then pushing.

To install as a hook that executes with every `git commit`:

```shell
$ prek install
```

## Pull Request Titles

Titles for pull requests should follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.

This is a lightweight convention on top of commit messages. It provides a simple set of rules for creating an explicit, readable, and automation-friendly project history.

Individual commit messages in branches may follow an unrestricted policy, but **PR titles must follow Conventional Commits**.

### Why We Use Conventional Commit PR Titles

We require PR titles to follow the Conventional Commits format because it:

- **Enables automatic changelogs** - the changelog is generated from PR titles when a release PR is opened; you do not need to edit `CHANGELOG.md` manually.
- **Clearly communicates intent** - reviewers can immediately see whether a PR is a `feat`, `fix`, `chore`, etc.
- **Improves git history navigation** - makes it easy to scan and understand changes over time.
- **Aligns with Semantic Versioning (SemVer)** - structured titles help determine version bumps automatically.
- **Supports better PR labeling & filtering** - PRs are labeled by type, making them easier to prioritise and review.
- **Flags breaking changes** - adding `!` (e.g. `feat!:`) automatically marks a PR as a breaking change.

### Format

The general structure is:

```text
<type>[optional scope]: <description>
```

Example:

```text
feat: send an email to the customer when a product is shipped
```

Types:

```text
feat — new feature
fix — bug fix
docs — documentation changes
style — formatting/styling (no code logic)
refactor — code changes without feature/bug impact
perf — performance improvements
test — adding/updating tests
build — changes to build system or dependencies
ci — changes to CI config/scripts
chore — miscellaneous maintenance tasks
revert — reverts an earlier commit
```

Put the one-line summary (and optional PR link) in the **title**; use the PR **description** for full context, rationale, and testing notes for reviewers.

## Releasing

To cut a release:

1. Open a pull request whose title matches the release pattern, e.g. `Release 0.4.13` or `release 0.4.13`.
2. Changelog CI will run, generate a new changelog section from PRs merged since the last GitHub release, and commit the updated `CHANGELOG.md` to that PR (and optionally comment the changelog on the PR).
3. After review and merge, maintainers create the GitHub release; the existing PyPI workflow will publish when the release is published.
