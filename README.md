[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](https://opensource.org/licenses/MIT)
[![Latest Version](https://img.shields.io/github/v/release/AI-SDC/ACRO?style=flat)](https://github.com/AI-SDC/ACRO/releases)
[![DOI](https://zenodo.org/badge/534172863.svg)](https://zenodo.org/badge/latestdoi/534172863)
[![PyPI package](https://img.shields.io/pypi/v/acro.svg)](https://pypi.org/project/acro)
[![Python versions](https://img.shields.io/pypi/pyversions/acro.svg)](https://pypi.org/project/acro)

[![Codacy](https://app.codacy.com/project/badge/Grade/a125e023fd7744d79cb42cd31f6ea05e)](https://www.codacy.com/gh/AI-SDC/ACRO/dashboard)
[![codecov](https://codecov.io/gh/AI-SDC/ACRO/branch/main/graph/badge.svg?token=VVHI41N05F)](https://codecov.io/gh/AI-SDC/ACRO)

*******************************************************************************

## ACRO: Tools for the Automatic Checking of Research Outputs

Statistical agencies and other custodians of secure facilities such as Trusted
Research Environments (TREs) routinely require the checking of research outputs
for disclosure risk. This can be a time-consuming and costly task, requiring
skilled staff.

ACRO (Automatic Checking of Research Outputs) is an open source
tool for automating the statistical disclosure control (SDC) of research
outputs. ACRO assists researchers and output checkers by distinguishing between
research output that is safe to publish, output that requires further analysis,
and output that cannot be published because of substantial disclosure risk.

It does this by providing a light-weight 'skin' that sits over well-known
analysis tools, in a variety of languages researchers might use. This adds
functionality to:

*   identify potentially disclosive outputs against a range of commonly used
    disclosure tests;
*   suppress outputs where required;
*   report reasons for suppression;
*   produce simple summary documents TRE staff can use to streamline their
    workflow.

![ACRO workflow and architecture schematic](docs/schematic.png)

See the project [wiki](https://github.com/AI-SDC/ACRO/wiki) for details.

## Coding standards
Are also described in the project [wiki](https://github.com/AI-SDC/ACRO/wiki)

*******************************************************************************


This work was funded by UK Research and Innovation under Grant Number MC_PC_23006 as part of Phase 1 of the DARE UK (Data and Analytics Research Environments UK) programme (https://dareuk.org.uk/), delivered in partnership with Health Data Research UK (HDR UK) and Administrative Data Research UK (ADR UK). The specific project was Semi-Automatic Checking of Research Outputs (SACRO).

<img src="docs/source/images/UK_Research_and_Innovation_logo.svg" width="20%" height="20%" padding=20/> <img src="docs/source/images/health-data-research-uk-hdr-uk-logo-vector.png" width="10%" height="10%" padding=20/> <img src="docs/source/images/logo_print.png" width="15%" height="15%" padding=20/>
