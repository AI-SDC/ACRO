==================
What ACRO Supports
==================

This page provides a comprehensive overview of ACRO's capabilities for researchers, developers, and non-technical stakeholders. ACRO supports a wide range of statistical analysis functions with semi-automated disclosure control.

.. note::
   **Drop-in Replacements:** ACRO functions are designed as direct replacements for standard analysis commands. Simply prefix your existing commands with ``acro.`` to enable automatic disclosure checking.

Supported Data Analysis Functions
==================================

Table Creation & Cross-tabulation
----------------------------------

**For Researchers:**
Create frequency tables and cross-tabulations with automatic cell suppression for small counts.

**What ACRO Supports:**

* **crosstab()** - Cross-tabulation of two or more variables with frequency counting
* **pivot_table()** - Spreadsheet-style pivot tables with aggregation functions
* **table()** - Simple frequency tables for categorical data (R interface only)

**Technical Details:**
- ACRO suppresses, and reports the reason why, the value of an aggregation statistic (mean, median, variance, etc.) for any cell is deemed to be sensitive
- The current version of ACRO supports the three most common tests for sensitivity: ensuring the number of contributors is above a frequency threshold, and testing for dominance via N-K rules
- **N-K Rule**: A dominance test where if the top N contributors account for more than K% of the total, the cell is considered disclosive
- **Frequency Threshold**: Cells with fewer than a specified number of contributors are suppressed
- All thresholds are configurable via YAML configuration files
- For detailed methodology, see our `research paper <https://doi.org/10.1109/TP.2025.3566052>`_
- Automatic flagging of negative or missing values for human review

**Example Use Cases:**
- Survey response analysis by demographics
- Clinical trial outcome tables
- Market research cross-tabulations
- Educational assessment reporting

Statistical Modeling
---------------------

**For Researchers:**
Run regression analyses with semi-automated checks on model outputs and residual degrees of freedom.

**What ACRO Supports:**

* **ols()** - Ordinary Least Squares linear regression
* **logit()** - Logistic regression for binary outcomes
* **probit()** - Probit regression for binary outcomes

**Technical Details:**
- For regressions such as linear, probit, and logit, the tests verify that the number of residual degrees of freedom exceeds a threshold
- Within the ACRO Python package, the functionality of the 'ACRO' class is split into a number of separate classes for maintainability and extensibility. A 'Tables' class contains the code necessary to perform disclosure checks on tabular data, such as crosstab. A separate 'Regression' class contains the code for checking regressions such as logit and probit

**Example Use Cases:**
- Economic modeling and policy analysis
- Medical research and clinical studies
- Social science research
- Business analytics and forecasting

Programming Language Support
============================

Python (Primary)
-----------------

**For Developers:**
The ACRO package is a lightweight Python tool that sits over well-known analysis tools that produce outputs such as tables, plots, and statistical models

**Supported Libraries:**
- **Pandas** - For data manipulation and table creation
- **Statsmodels** - For statistical modeling and regression analysis
- **NumPy** - For numerical computations

**Python Version Support:**
- Python 3.10, 3.11, 3.12, 3.13

R Language
----------

**For R Users:**
Additional programming languages such as this R package are supported by providing front-end packages that interface with the core ACRO Python back-end

**Integration Features:**
- Native R syntax and workflows
- R Markdown and Shiny application support
- Tidyverse compatibility
- CRAN package availability

**Getting Started in R:**
```r
library("acro")
acro_init(suppress = TRUE)
```

Stata Integration
-----------------

**For Stata Users:**
ACRO is designed to let you use familiar commands in R, Stata and Python

**Features:**
- Drop-in replacement for standard Stata commands
- Familiar Stata syntax and workflows
- Integration with existing Stata scripts

Disclosure Control Features
===========================

semi-automated Sensitivity Testing
------------------------------

**What ACRO Checks:**

**For Tables:**
- Minimum cell counts (frequency thresholds)
- Dominance rules (N-K rules for concentration)
- Presence of negative or missing values

**For Statistical Models:**
- Residual degrees of freedom thresholds
- Model fit diagnostics
- Parameter significance testing

**For Non-Technical Users:**
ACRO automatically identifies when research outputs might reveal sensitive information about individuals or organizations, applying industry-standard privacy protection rules. It must be used by trained researchers and checked by skilled checkers.

Output Management
-----------------

**What ACRO Provides:**

* **Suppression Masks** - Clear indication of which results are hidden and why
* **Summary Reports** - Detailed explanation of all disclosure checks performed
* **Audit Trails** - Complete record of all analysis steps and decisions
* **Exception Handling** - Process for requesting release of flagged outputs

**Workflow Integration:**
The finalise function will: Check that each output with "fail" or "review" status has an exception, if not you will be asked to enter one. Write the outputs to a directory. This directory contains everything that the output checkers need to make a decision

Supported Environments
======================

Research Environments
----------------------

**Where ACRO Works:**
- Trusted Research Environments (TREs)
- Data safe havens
- Secure data centers
- Academic research computing facilities
- Government statistical offices
- Healthcare research environments

**Installation:**
See :doc:`installation` for complete installation instructions and system requirements.

Integration Capabilities
========================

Analysis Workflows
------------------

**For Research Teams:**
ACRO integrates seamlessly into existing data analysis workflows, requiring minimal changes to current practices while adding comprehensive privacy protection.

**Supported Workflows:**
- Jupyter notebook analysis
- R Markdown documents
- Stata do-files and scripts
- Batch processing and automation
- Interactive analysis sessions

**Data Sources:**
- CSV and Excel files
- Database connections
- Survey data platforms
- Administrative datasets
- Clinical trial databases

Output Formats
--------------

**What ACRO Produces:**
- Standard CSV files for tables
- JSON metadata files for automation
- Excel workbooks for human reviewers

**Review Process Support:**
Compatible with SACRO-Viewer for interactive output review by data controllers and compliance officers.

Technical Architecture
======================

**For System Administrators:**

**Core Technology:**
Lightweight translation scripts intercept your commands and pass them through to a python 'engine', based on industry-standard packages that run your commands and perform statistical disclosure checks on them

**System Requirements:**
- Python 3.10+ runtime environment
- Standard scientific computing libraries (pandas, numpy, statsmodels)
- Minimal computational overhead
- No external network dependencies during analysis

**Security Features:**
- Local processing only (no cloud dependencies)
- Audit logging and tracking
- Configurable disclosure thresholds
- Role-based access controls (through integration with TRE systems)

**Documentation and Support:**
Standard Python coding and naming practices have been used throughout. GitHub continuous integration (CI) runners automatically generate and publish API documentation using the Python docstrings written in numpydoc format

What ACRO Does NOT Support
===========================

**Current Limitations:**
- Complex visualizations and plots (coming in future versions)
- Time series analysis (specialized disclosure rules needed)
- Machine learning models (use SACRO-ML for AI/ML workflows)
- Real-time data streams
- Distributed computing frameworks

**Alternative Solutions:**
- **SACRO-ML** - For machine learning and AI model disclosure control
- **SACRO-Viewer** - For interactive output review and approval
- **Traditional SDC tools** - For specialized use cases not covered by ACRO

Getting Help
============

**For All Users:**
- Comprehensive online documentation at GitHub Pages
- Built-in help system: ``help(acro.function_name)``
- Example notebooks and tutorials in the GitHub repository
- Active community support and issue tracking

**For Researchers:**
- Step-by-step tutorials for common analysis patterns
- Best practices guides for different research domains
- Integration examples for popular data science workflows

**For Developers:**
- Complete API documentation with examples
- Contributing guidelines and development setup
- Continuous integration and testing frameworks
- Open source development model with community contributions
