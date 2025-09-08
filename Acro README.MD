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
- [API Reference](#api-reference)  
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
### Understanding Output
ACRO provides three types of feedback:

- ✅ PASS - Safe to release
- ❌ FAIL - Needs justification (e.g., small cell counts)
- ⚠️ REVIEW - Manual review required (e.g., missing values)

Example output:

