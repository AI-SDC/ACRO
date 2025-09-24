========================================
Welcome to the AI-SDC family of tools
========================================

This organisation holds the code repositories for the **SACRO** family of tools:

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Documentation

   introduction
   support
   installation
   user_guide
   examples
   api

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: SACRO Tools

   acro
   sacro_ml
   acro_r
   sacro_viewer

.. grid:: 2

    .. grid-item-card:: ACRO (Python)
        :link: introduction
        :link-type: doc
        :shadow: md
        :class-header: bg-primary text-white

        **Statistical Disclosure Control for Python**
        
        Tools for the Semi-Automatic Checking of Research Outputs. Drop-in replacements for common analysis commands with built-in privacy protection.
        
        +++
        
        :bdg-primary:`Current Documentation Focus` :doc:`Get Started → <introduction>`

    .. grid-item-card:: SACRO-ML
        :link: sacro_ml
        :link-type: doc
        :shadow: md
        :class-header: bg-info text-white

        **Machine Learning Privacy Tools**
        
        Collection of tools and resources for managing the statistical disclosure control of trained machine learning models.

        +++
        
        :bdg-info:`ML Privacy` :doc:`Learn More → <sacro_ml>`

.. grid:: 2

    .. grid-item-card:: ACRO-R
        :link: acro_r
        :link-type: doc
        :shadow: md
        :class-header: bg-success text-white

        **R Package Integration**
        
        ACRO R Package: Tools for the Semi-Automatic Checking of Research Outputs for R users and workflows.

        +++
        
        :bdg-success:`R Integration` :doc:`Explore → <acro_r>`

    .. grid-item-card:: SACRO-Viewer
        :link: sacro_viewer
        :link-type: doc
        :shadow: md
        :class-header: bg-warning text-dark

        **Output Checking Interface**
        
        A tool for fast, secure and effective output checking, which can work in any TRE (Trusted Research Environment).

        +++
        
        :bdg-warning:`GUI Tool` :doc:`View Docs → <sacro_viewer>`

ACRO: Statistical Disclosure Control
====================================

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

Getting Started
===============

.. grid:: 3

    .. grid-item-card:: Install
        :link: installation
        :link-type: doc
        :class-header: bg-light

        Get ACRO installed and configured in your environment

    .. grid-item-card:: Learn
        :link: examples
        :link-type: doc
        :class-header: bg-light

        Explore tutorials and examples for common use cases

    .. grid-item-card:: Reference
        :link: api
        :link-type: doc
        :class-header: bg-light

        Complete API documentation and function reference

Key Methods
-----------

* :py:meth:`~acro.ACRO.crosstab` - Create cross-tabulations with disclosure checking
* :py:meth:`~acro.ACRO.pivot_table` - Create pivot tables with disclosure checking  
* :py:meth:`~acro.ACRO.ols` - Ordinary least squares regression with disclosure checking
* :py:meth:`~acro.ACRO.finalise` - Prepare outputs for review by data controllers

Community and Support
=====================

.. grid:: 2

    .. grid-item-card:: Get Help
        :class-header: bg-light

        * `GitHub Issues <https://github.com/AI-SDC/ACRO/issues>`_
        * `Discussion Forum <https://github.com/AI-SDC/ACRO/discussions>`_
        * Email: acro-support@ai-sdc.org

    .. grid-item-card:: Contribute
        :class-header: bg-light

        * `Contributing Guide <https://github.com/AI-SDC/ACRO/blob/main/CONTRIBUTING.md>`_
        * `Source Code <https://github.com/AI-SDC/ACRO>`_
        * `Report Issues <https://github.com/AI-SDC/ACRO/issues/new>`_

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`