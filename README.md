## ACRO: Tools for the Semi-Automatic Checking of Research Outputs

[![DOI](https://zenodo.org/badge/534172863.svg)](https://zenodo.org/badge/latestdoi/534172863)
[![PyPI package](https://img.shields.io/pypi/v/acro.svg)](https://pypi.org/project/acro)
[![Python versions](https://img.shields.io/pypi/pyversions/acro.svg)](https://pypi.org/project/acro)
[![Codacy](https://app.codacy.com/project/badge/Grade/a125e023fd7744d79cb42cd31f6ea05e)](https://app.codacy.com/gh/AI-SDC/ACRO/dashboard)
[![codecov](https://codecov.io/gh/AI-SDC/ACRO/branch/main/graph/badge.svg?token=VVHI41N05F)](https://codecov.io/gh/AI-SDC/ACRO)

ACRO is a free and open source tool that supports the semi-automated checking of research outputs (SACRO) for privacy disclosure within secure data environments. SACRO is a framework that applies best-practice principles-based [statistical disclosure control](https://en.wikipedia.org/wiki/Statistical_disclosure_control) (SDC) techniques on-the-fly as researchers conduct their analysis. SACRO is designed to assist human checkers rather than seeking to replace them as with current automated rules-based approaches.

The ACRO package is a lightweight Python tool that sits over well-known analysis tools that produce outputs such as tables, plots, and statistical models. This package adds functionality to:

* automatically identify potentially disclosive outputs against a range of commonly used disclosure tests;
* apply optional disclosure mitigation strategies as requested;
* report reasons for applying SDC;
* and produce simple summary documents trusted research environment staff can use to streamline their workflow and maintain auditable records.

This creates an explicit change in the dynamics so that SDC is something done with researchers rather than to them, and enables more efficient communication with checkers.

A graphical user interface ([SACRO-Viewer](https://github.com/AI-SDC/SACRO-Viewer)) supports human checkers by displaying the requested output and results of the checks in an immediately accessible format, highlighting identified issues, potential mitigation options, and tracking decisions made.

Additional programming languages used by researchers are supported by providing front-end packages that interface with the core ACRO Python back-end; for example, see the R wrapper package: [ACRO-R](https://github.com/AI-SDC/ACRO-R).

![ACRO workflow and architecture schematic](docs/schematic.png)

### Installation

ACRO can be installed via [PyPI](https://pypi.org/project/acro/).

If installed in this way, the example [notebooks](notebooks) and the [data](data) files used therein will need to be copied from the repository.

```
$ pip install acro
```

### Examples

See the example notebooks for:

* [Python charities dataset](notebooks/test.ipynb)
* [Python nursery dataset](notebooks/test-nursery.ipynb)
* [R charities dataset](https://ai-sdc.github.io/ACRO/_static/test.nb.html)
* [R nursery dataset](https://ai-sdc.github.io/ACRO/_static/test-nursery.nb.html)

### Documentation

The github-pages contains pre-built [documentation](https://ai-sdc.github.io/ACRO/).

### Training Materials

For training videos about ACRO, see [training videos](https://drive.google.com/drive/folders/1z5zKuZdiNth0c7CLBt3vDEyhGwSIocw_).

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

### Acknowledgement

This work was funded by UK Research and Innovation under Grant Number MC_PC_23006 as part of Phase 1 of the [DARE UK](https://dareuk.org.uk) (Data and Analytics Research Environments UK) programme, delivered in partnership with Health Data Research UK (HDR UK) and Administrative Data Research UK (ADR UK). The specific project was Semi-Automatic Checking of Research Outputs (SACRO).

<img src="docs/source/images/UK_Research_and_Innovation_logo.svg" width="20%" height="20%" padding=20/> <img src="docs/source/images/health-data-research-uk-hdr-uk-logo-vector.png" width="10%" height="10%" padding=20/> <img src="docs/source/images/logo_print.png" width="15%" height="15%" padding=20/>
