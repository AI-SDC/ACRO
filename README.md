## ACRO: Tools for the Automatic Checking of Research Outputs

[![DOI](https://zenodo.org/badge/534172863.svg)](https://zenodo.org/badge/latestdoi/534172863)
[![PyPI package](https://img.shields.io/pypi/v/acro.svg)](https://pypi.org/project/acro)
[![Python versions](https://img.shields.io/pypi/pyversions/acro.svg)](https://pypi.org/project/acro)
[![Codacy](https://app.codacy.com/project/badge/Grade/a125e023fd7744d79cb42cd31f6ea05e)](https://app.codacy.com/gh/AI-SDC/ACRO/dashboard)
[![codecov](https://codecov.io/gh/AI-SDC/ACRO/branch/main/graph/badge.svg?token=VVHI41N05F)](https://codecov.io/gh/AI-SDC/ACRO)

This repository holds the Python ACRO package. An R wrapper package is available: [ACRO-R](https://github.com/AI-SDC/ACRO-R).

A GUI for viewing and approving outputs is also available: [SACRO-Viewer](https://github.com/AI-SDC/SACRO-Viewer)

ACRO (Automatic Checking of Research Outputs) is an open source tool for automating the [statistical disclosure control](https://en.wikipedia.org/wiki/Statistical_disclosure_control) (SDC) of research outputs. ACRO assists researchers and output checkers by distinguishing between research output that is safe to publish, output that requires further analysis, and output that cannot be published because of a substantial risk of disclosing private data.

It does this by providing a lightweight 'skin' that sits over well-known analysis tools, in a variety of languages researchers might use. This adds functionality to:

*   identify potentially disclosive outputs against a range of commonly used disclosure tests;
*   suppress outputs where required;
*   report reasons for suppression;
*   produce simple summary documents TRE staff can use to streamline their workflow.

![ACRO workflow and architecture schematic](docs/schematic.png)

### Installation

ACRO can be installed via [PyPI](https://pypi.org/project/acro/).

If installed in this way, the example [notebooks](notebooks) and the [data](data) files used therein will need to be copied from the repository.

```
$ pip install acro
```

#### Notes for Python 3.13

ACRO currently depends on numpy version 1.x.x for which no pre-compiled wheels are available within pip for Python 3.13. Therefore, in this scenario, numpy must be built from source. This requires the installation of a C++ compiler before pip installing acro.

For Windows, the [Microsoft Visual Studio C++ build tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) will likely need to be installed first.

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
