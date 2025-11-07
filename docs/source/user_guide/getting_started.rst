===============
Getting Started
===============

This guide helps you get up and running with ACRO for statistical disclosure control.

What is ACRO?
=============

ACRO (Automatic Checking of Research Outputs) is a Python package that provides statistical disclosure control for research outputs. It acts as a wrapper around common analysis functions, automatically checking for potential privacy disclosures.

Key Concepts
============

Statistical Disclosure Control (SDC)
------------------------------------

SDC is the process of protecting confidential information in statistical data releases. ACRO implements principles-based SDC that:

* Identifies potentially disclosive outputs
* Applies mitigation strategies when needed
* Maintains detailed audit trails
* Supports human checker workflows

Disclosure Types
----------------

ACRO checks for several types of disclosure:

* **Identity disclosure** - When individuals can be identified
* **Attribute disclosure** - When sensitive attributes can be inferred
* **Inferential disclosure** - When statistical inference reveals information

Safety Thresholds
-----------------

ACRO uses configurable thresholds to determine safety:

* **Minimum cell count** - Default: 10 observations
* **P-ratio threshold** - Default: 0.1 for dominance
* **NK-rule** - Default: n=2, k=85% for concentration

Basic Workflow
==============

1. **Initialize ACRO session**
2. **Run analysis with ACRO methods**
3. **Review disclosure warnings**
4. **Finalize outputs for checking**

Installation Requirements
=========================

* Python 3.10 or higher
* pandas >= 1.5.0
* statsmodels >= 0.13.0
* PyYAML for configuration

Next Steps
==========

* See :doc:`core_concepts` for detailed methodology
* Check :doc:`configuration` for customization options
* Visit :doc:`../examples` for hands-on tutorials
