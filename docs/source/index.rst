===============================
Welcome to the AI-SDC family of tools
===============================

This organisation holds the code repositories for the **SACRO** family of tools:

.. grid:: 2

    .. grid-item-card:: ACRO (Python)
        :img-top: ./images/user_guide.png
        :link: getting_started
        :shadow: md

        Tools for the Semi-Automatic Checking of Research Outputs. These are tools for researchers to use as drop-in replacements for common analysis commands.
        
        +++
        
        :bdg-primary:`Current Documentation Focus`

    .. grid-item-card:: SACRO-ML
        :img-top: ./images/user_guide.png
        :link: getting_started
        :shadow: md

        Collection of tools and resources for managing the statistical disclosure control of trained machine learning models.

        +++
        
        :bdg-info:`See API documentation`

.. grid:: 2

    .. grid-item-card:: ACRO-R
        :img-top: ./images/examples.png
        :link: examples
        :shadow: md

        ACRO R Package: Tools for the Semi-Automatic Checking of Research Outputs for R users and workflows.

        +++
        
        :bdg-info:`See API documentation`

    .. grid-item-card:: SACRO-Viewer
        :img-top: ./images/api.png
        :link: api
        :shadow: md

        A tool for fast, secure and effective output checking, which can work in any TRE (Trusted Research Environment).

        +++
        
        :bdg-info:`See API documentation`

Welcome to ACRO 
================

ACRO is a free and open source tool that supports the semi-automated checking of research outputs (SACRO) for privacy disclosure within secure data environments. This package acts as a lightweight Python tool that sits over well-known analysis tools to provide statistical disclosure control.

.. note::
   **New in v0.4.8:** Enhanced support for complex statistical models and improved R integration.

What is ACRO?
=============

ACRO implements a principles-based statistical disclosure control (SDC) methodology that:

* Automatically identifies potentially disclosive outputs
* Applies optional disclosure mitigation strategies
* Reports reasons for applying SDC
* Produces summary documents for output checkers

Quick Example
=============

.. code-block:: python

   import acro

   # Initialize ACRO
   acro = acro.ACRO(suppress=True)

   # Create a cross-tabulation with automatic disclosure checking
   safe_table = acro.crosstab(
       df.column1, 
       df.column2, 
       show_suppressed=True
   )

   # Finalize outputs for review
   acro.finalise(output_folder="outputs")

Core Features
=============

Automated Disclosure Checking
-----------------------------

ACRO automatically runs disclosure tests on your outputs, checking for:

* Small cell counts in tables
* Threshold disclosure in statistical models
* Identity disclosure risks

Integration with Popular Libraries
----------------------------------

Works seamlessly with:

* **Pandas** - for data manipulation and table creation
* **Statsmodels** - for statistical modeling
* **R and Stata** - through wrapper packages

API Overview
============

.. py:class:: ACRO(suppress=True, config=None)

   The main ACRO class provides the interface for all disclosure checking functionality.

   :param suppress: Whether to suppress potentially disclosive outputs
   :type suppress: bool
   :param config: Configuration options for disclosure checking
   :type config: dict, optional

Parameters
----------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Parameter
     - Type
     - Description
   * - suppress
     - bool
     - Whether to suppress potentially disclosive outputs
   * - config
     - dict, optional
     - Configuration options for disclosure checking

Key Methods
-----------

* ``crosstab()`` - Create cross-tabulations with disclosure checking
* ``pivot_table()`` - Create pivot tables with disclosure checking
* ``ols()`` - Ordinary least squares regression with disclosure checking
* ``finalise()`` - Prepare outputs for review by data controllers

Examples
========

* Jupyter Notebooks
* R Integration
* Stata Integration

Resources
=========

* FAQ
* Troubleshooting
* Contributing
* Changelog

Next Steps
==========

* Install ACRO and set up your environment
* Follow the Quick Start Guide for your first analysis
* Explore the Example Notebooks for common use cases
* Check the API Reference for detailed documentation