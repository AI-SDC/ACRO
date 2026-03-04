# Contributing

Contributions to this repository are very welcome. Please create an issue before starting any significant work so that we can discuss and understand the changes. If you are interested in contributing, feel free to contact us or create an issue in the [issue tracking system](https://github.com/AI-SDC/ACRO/issues). Alternatively, you may [fork](https://docs.github.com/en/github/getting-started-with-github/fork-a-repo) the project and submit a [pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork). All contributions must be made under the same license as the rest of the project: [MIT License](../blob/main/LICENSE). New code should be accompanied with appropriate unit tests and documentation; `CHANGELOG.md` is generated from PR titles (see [Changelog](#changelog) below). If this is your first contribution to the repository, please also add your details to `CITATION.cff`. If you are introducing new imports, then these must also be added to `requirements.txt` (in root and docs folders) and `setup.py`. After creating a pull request, the continuous integration tools will automatically run the unit tests, apply the pre-commit checks listed below, and build and deploy the Sphinx documentation (when merged into the main branch.)

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

- **Enables automatic changelogs** - release notes can be generated from PR titles without manual work.
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

## Changelog

`CHANGELOG.md` is generated from commit history using [git-cliff](https://github.com/orhun/git-cliff). Entries come from merged PR titles (via squash-merge commit messages) and are formatted to match the existing changelog style.

### Generate the changelog

To generate or update the changelog locally:

1. Install git-cliff from the [releases page](https://github.com/orhun/git-cliff/releases) or via a package manager:

   ```shell
   # cargo
   cargo install git-cliff

   # homebrew (macOS / Linux)
   brew install git-cliff
   ```

2. Run from an up-to-date branch:

   ```shell
   scripts/generate_changelog.sh
   ```

3. Review and edit `CHANGELOG.md` as needed, then commit:

   ```shell
   git add CHANGELOG.md
   git commit -m "docs: update changelog"
   ```

The script updates the current top `## Version ...` section by inserting only newly generated entries. Re-running is safe: exact duplicate lines are not inserted again.

### Quick verification (copy/paste)

```shell
scripts/generate_changelog.sh
sed -n '1,30p' CHANGELOG.md
scripts/generate_changelog.sh
```

The second run should print: `No new changelog entries to add under the current top version.`

If you were only testing and do not want to keep generated edits:

```shell
git restore CHANGELOG.md
```

### Where entries come from

Entries are derived from **commit messages** on the branch you run from. git-cliff scans commits since the last release tag and keeps those that follow Conventional Commits. It does not use GitHub PR metadata, so it works even when no PR exists yet.

- **No PR yet**: You can run the script on a feature branch before opening or merging a PR. Entries will reflect your commit messages (e.g. issue refs like `#327`). After the PR is squash-merged, running on `main` will pick up the squash commit with the PR number (e.g. `#352`).
- **Branch matters**: You can run on any branch to preview entries. For correct PR numbers and links in the final changelog, run on up-to-date `main` after PRs are merged.
- **PR links**: A line gets a PR link like `([#NNN](https://github.com/AI-SDC/ACRO/pull/NNN))` only if the commit message contains `(#NNN)`. If the commit message is `docs: update citation` with no PR reference, the changelog line will have no link.
- **Squash-merge**: Use "Squash and merge" when merging PRs so the default commit message includes the PR number (e.g. `feat: add X (#123)`). That ensures the changelog entry gets the link.

### Configuration

The configuration lives in `cliff.toml` at the repository root. It:

- Converts `(#NNN)` in commit messages into markdown PR links.
- Skips noise commits (pre-commit auto-fixes, changelog and release-prep commits).
- Filters out commits that do not follow Conventional Commits (see [Pull Request Titles](#pull-request-titles)).
