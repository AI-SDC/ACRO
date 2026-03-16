# Contributing

Contributions to this repository are very welcome. If this is your first contribution to the repository, please ensure that you have carefully read and understood the entirety of this contributing guide and our [AI Policy](AI_POLICY.md).

Please create an issue before starting any significant work so that we can discuss and understand the changes before you invest time in it. You can contact us directly or use the [issue tracking system](https://github.com/AI-SDC/ACRO/issues). Once agreed, external collaborators should [fork](https://docs.github.com/en/github/getting-started-with-github/fork-a-repo) the project and submit a [pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork) (PR). If you are a member of the repository team, your changes should be made in a feature branch before opening a PR.

## Pull Request Standards

All PRs **must** meet the following requirements before being accepted.

### Provenance and legal

- Contributors assert copyright ownership and release their contribution under the [MIT License](../blob/main/LICENSE).
- All contributor details are present in `CITATION.cff`. First-time contributors must add themselves.
- If work is copied from another open source repository, the license must be checked and included.

### Code quality

- The PR is small and addresses a single specific issue.
- Code is high quality. This includes: small focused functions and modules, no duplication, fully documented, extensive use of type hints, no unused arguments, no more than 3 levels of nesting except in rare justified cases, no bloat.
- No inline pragmas. If a rule suppression is genuinely necessary, add a per-file setting to `pyproject.toml` to keep the source code clean.
- New dependencies are added to `pyproject.toml`.
- All [pre-commit checks](#pre-commit) pass, including automatic formatting and linting. Run [pre-commit](#pre-commit) locally before opening a PR.

### Tests

- All existing tests pass.
- New code is accompanied by appropriate tests.
- Code coverage is at least 90% statement coverage.
- Tests verify real-world effects, not just that lines of code execute.
- Run the full test suite locally before opening a PR. CI minutes are not unlimited.

### Pull request description

- The PR title follows [Conventional Commits](#pull-request-titles) format.
- The description is **short**, written in your own words, and explains what changed and why. See the [AI Contributions Policy](AI_CONTRIBUTIONS_POLICY.md) for what this means in practice. AI-generated descriptions are not acceptable.
- Do not add issue or PR numbers to the title manually. To close an issue automatically, add the closing keyword in a comment instead.

### AI

- Any use of AI tools to assist with code or documentation is disclosed in the opening PR comment, including the specific tool and version. See the [AI Contributions Policy](AI_CONTRIBUTIONS_POLICY.md) for the full requirements.

## Development

Clone the repository and install the dependencies within a virtual environment:

```shell
$ git clone git@github.com:AI-SDC/ACRO.git
$ cd ACRO
$ pip install -e .[test]
```

Run the tests:

```shell
$ pytest
```

## Directory Structure

| Directory   | Contents                                           |
| ----------- | -------------------------------------------------- |
| `acro`      | ACRO source code                                   |
| `data`      | Data files for testing                             |
| `docs`      | [Sphinx](https://www.sphinx-doc.org) documentation |
| `notebooks` | Example notebooks                                  |
| `stata`     | Stata wrapper code                                 |
| `test`      | Unit tests                                         |

## Pre-commit

Code quality is maintained through [pre-commit](https://prek.j178.dev) hooks that run [Ruff](https://github.com/astral-sh/ruff) along with other formatting and linting tools. A `.pre-commit-config.yaml` configuration file is provided to automatically handle:

- Trimming trailing whitespace and fixing line endings
- Spell checking
- Validating JSON, TOML, YAML, etc., files
- Formatting and linting with Ruff
- Checking types with mypy
- And others

We recommend using [uv](https://docs.astral.sh/uv/) to install prek:

```shell
uv tool install prek
```

However, you may prefer to use pip:

```shell
pip install prek
```

Run on all files locally:

```shell
prek run -a
```

Optionally, install as a git hook so it runs automatically on every commit:

```shell
prek install
```

Make any corrections and re-run before committing.


## Pull Request Titles

PR titles **must** follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification. Individual commit messages within a branch are unrestricted, but the PR title is used to generate the changelog and must be correct.

### Format

```text
<type>[optional scope]: <description>
```

Example:

```text
feat: send an email to the customer when a product is shipped
```

### Types

| Type       | Use for                                          |
| ---------- | ------------------------------------------------ |
| `feat`     | New feature                                      |
| `fix`      | Bug fix                                          |
| `docs`     | Documentation changes only                       |
| `style`    | Formatting or styling with no logic change       |
| `refactor` | Code restructuring without feature or bug impact |
| `perf`     | Performance improvements                         |
| `test`     | Adding or updating tests                         |
| `build`    | Build system or dependency changes               |
| `ci`       | CI configuration or script changes               |
| `chore`    | Miscellaneous maintenance                        |
| `revert`   | Reverting an earlier commit                      |

To flag a breaking change, append `!` to the type: `refactor!: renamed foo() to goo()`.

### Why we use Conventional Commit PR titles

We require PR titles to follow the Conventional Commits format because it:

* Enables automatic changelogs - release notes can be generated from PR titles without manual work.
* Clearly communicates intent - reviewers can immediately see whether a PR is a `feat`, `fix`, `chore`, etc.
* Improves git history navigation - makes it easy to scan and understand changes over time.
* Aligns with Semantic Versioning (SemVer) - structured titles help determine version bumps automatically.
* Supports better PR labeling and filtering - PRs are labeled by type, making them easier to prioritise and review.
* Flags breaking changes - adding `!` (e.g. `feat!:`) automatically marks a PR as a breaking change.

## Changelog

`CHANGELOG.md` is generated from the commit history using [git-cliff](https://github.com/orhun/git-cliff) and assumes Conventional Commit messages. The configuration lives in `cliff.toml` at the repository root, which converts `(#NNN)` references into markdown PR links and skips noise commits such as pre-commit auto-fixes and release-prep commits.

### Install git-cliff

```shell
uv tool install git-cliff
# or
pip install git-cliff
```

### Generate the changelog

Example that prepends entries from a given tag to HEAD:

```shell
git-cliff v0.4.12..HEAD --config cliff.toml --prepend CHANGELOG.md
```

Adjust the tag to match the last release you want to start from.
