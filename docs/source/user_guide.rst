==========
User Guide
==========

Complete guide to using ACRO for statistical disclosure control.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/getting_started
   user_guide/core_concepts
   user_guide/configuration
   user_guide/architecture

Overview
========

This user guide provides comprehensive documentation for using ACRO effectively in your
research workflows.  If you are new to ACRO, start with :doc:`user_guide/getting_started`.
If you want to understand *how* the disclosure checking works, see
:doc:`user_guide/core_concepts` and :doc:`user_guide/architecture`.

Quick Navigation
================

* **New users**: Start with :doc:`user_guide/getting_started`
* **Understand the checks**: Read :doc:`user_guide/core_concepts`
* **Configure thresholds**: See :doc:`user_guide/configuration`
* **Developers / TRE admins**: See :doc:`user_guide/architecture`
* **Hands-on examples**: Browse :doc:`examples`

Key Topics
==========

Data Analysis
-------------

* **Cross-tabulations**  Safe table creation with automatic disclosure control
* **Statistical modelling**  Regression analysis with privacy protection
* **Summary statistics**  Descriptive statistics with safety checks
* **Data visualisation**  Safe histograms and survival plots

Mitigation Strategies
---------------------

* **Suppression**  Remove records that fall into disclosive cells, then rerun the table
* **Rounding**  Round all cell values to the nearest multiple of a configurable base

Configuration
-------------

* **Safety parameters**  Customising disclosure thresholds via YAML
* **Federated mode**  Evidence-only mode for use with a trusted aggregator
* **Ontology knowledge base**  How the JSON lookup files are generated and updated

Integration
-----------

* **Python workflows**  Jupyter notebook integration
* **R integration**  Using the ACRO-R package
* **Stata workflows**  Statistical software integration

Best Practices
==============

1. **Use** ``suppress=True`` **or** ``enable_rounding()`` in production environments.
2. **Review** all ``review`` and ``fail`` outputs before calling ``finalise()``.
3. **Name your outputs** with ``rename_output()`` for easier output checker review.
4. **Document your analysis**  add comments and exceptions as you go.
5. **Test with synthetic data** before running on sensitive datasets.

Getting Help
============

* :doc:`api`  Complete API reference
* `GitHub Issues <https://github.com/AI-SDC/ACRO/issues>`_  Report bugs
* `Discussions <https://github.com/AI-SDC/ACRO/discussions>`_  Community support
