# ACRO: Semi-Automated Statistical Disclosure Control Tool

[![PyPI](https://img.shields.io/pypi/v/acro.svg)](https://pypi.org/project/acro/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/AI-SDC/ACRO)](https://github.com/AI-SDC/ACRO/issues)

ACRO is a lightweight, open-source tool that helps researchers automatically check tables, regressions, and plots for privacy disclosure risks in secure data environments. 

It runs privacy checks in real-time during analysis, flags risky results, and generates auditable trails to support output checkers effectively.

---

## Table of Contents

- [Overview](https://github.com/AI-SDC/ACRO/blob/270-documentation-update-structure-for-readmemd/Acro%20README.MD#overview) 
- [Quick Start](#quick-start)
- [Installation](#installation)  
- [Understanding ACRO Output](#understanding-acro-output)  
- [Configuration](#configuration)  
- [Examples](#examples)  
- [Documentation](#documentation)  
- [Support](#support)  
- [Contributing](#contributing)  
- [License](#license)  
- [Citation](#citation)  
- [Acknowledgments](#acknowledgments)  

---
## Overview

ACRO acts as a drop-in replacement for common analysis commands, adding privacy-preserving statistical disclosure control checks on the fly. It transforms standard workflows by running analysis and privacy checks simultaneously across Python, R, and Stata.

A graphical user interface ([SACRO-Viewer](https://github.com/AI-SDC/SACRO-Viewer)) supports human checkers by displaying the requested output and results of the checks in an immediately accessible format, highlighting identified issues, potential mitigation options, and tracking decisions made.

![ACRO workflow and architecture schematic](docs/schematic.png)

### Key Features

- Intercepts commands like crosstabs, regressions, and plots  
- Applies real-time statistical disclosure control checks  
- Flags potentially disclosive outputs  
- Generates audit trails for output checkers  
- Familiar syntax across Python, R, and Stata  

---

## Quick Start
---

## Installation

### Prerequisites

- Python 3.9+  
- R 4.0+ (for R users)  
- Stata 16+ (for Stata users)  

### Python Example
```
pip install acro
python -c "
import acro
session = acro.ACRO()
print('✅ ACRO is ready!')
"
```
## Understanding Output
ACRO provides three types of feedback:

- ✅ PASS - Safe to release
- ❌ FAIL - Needs justification (e.g., small cell counts)
- ⚠️ REVIEW - Manual review required (e.g., missing values)

Example output:
```
Summary:
  Status: review
  Output: crosstab

Disclosivity:
  Rows: 2
  Columns: 3
  Cells: 6
  Non-disclosive cells: 4
  Disclosive cells: 2
  
Details:
  Cell (0,1): threshold; count 5 < 10
  Cell (1,2): threshold; count 7 < 10
```


## Configuration

---

## Example
---

## Documentation
- [API Documentation](https://ai-sdc.github.io/ACRO/)- The github-pages contains pre-built.
- [Examples](https://github.com/AI-SDC/ACRO#examples) - Jupyter notebooks with real examples
- [FAQ](https://github.com/AI-SDC/ACRO#faq)  

## Support

- [Issues](https://github.com/AI-SDC/ACRO/issues)- Bug reports and feature requests
- [Discussions](https://github.com/AI-SDC/ACRO/discussions)- Questions and community help
- [Contributing](https://github.com/AI-SDC/ACRO/blob/main/CONTRIBUTING.md)- How to contribute

## Acknowledgement

This work was funded by UK Research and Innovation under Grant Number MC_PC_23006 as part of Phase 1 of the [DARE UK](https://dareuk.org.uk) (Data and Analytics Research Environments UK) programme, delivered in partnership with Health Data Research UK (HDR UK) and Administrative Data Research UK (ADR UK). The specific project was Semi-Automatic Checking of Research Outputs (SACRO).

<img src="docs/source/images/UK_Research_and_Innovation_logo.svg" width="20%" height="20%" padding=20/> <img src="docs/source/images/health-data-research-uk-hdr-uk-logo-vector.png" width="10%" height="10%" padding=20/> <img src="docs/source/images/logo_print.png" width="15%" height="15%" padding=20/>
