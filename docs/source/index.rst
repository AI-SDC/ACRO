========================================
Welcome to the AI-SDC family of tools
========================================

Our tools are designed to help researchers assess the privacy disclosure risks of their outputs, including tables, plots, statistical models, and trained machine learning models


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


.. grid:: 2

    .. grid-item-card:: ACRO (Python)
        :link: introduction
        :link-type: doc
        :shadow: md
        :class-header: bg-primary

        **Statistical Disclosure Control for Python**

        Tools for the Semi-Automatic Checking of Research Outputs. Drop-in replacements for common analysis commands with built-in privacy protection.

        +++

        :bdg-primary:`Current Documentation Focus` :doc:`Get Started → <introduction>`

    .. grid-item-card:: SACRO-ML
        :link: sacro_ml
        :link-type: doc
        :shadow: md
        :class-header: bg-info

        **Machine Learning Privacy Tools**

        Collection of tools and resources for managing the statistical disclosure control of trained machine learning models.

        +++

        :bdg-info:`ML Privacy` :doc:`Learn More → <sacro_ml>`

.. grid:: 2

    .. grid-item-card:: ACRO-R
        :link: acro_r
        :link-type: doc
        :shadow: md
        :class-header: bg-success

        **R Package Integration**

        R-language interface for the Python ACRO library, providing familiar R syntax for statistical disclosure control.

        +++

        :bdg-success:`R Integration` :doc:`Explore → <acro_r>`

    .. grid-item-card:: SACRO-Viewer
        :link: sacro_viewer
        :link-type: doc
        :shadow: md
        :class-header: bg-warning

        **Graphical User Interface**

        A graphical user interface for fast, secure and effective output checking, which can work in any TRE (Trusted Research Environment).

        +++

        :bdg-warning:`GUI Tool` :doc:`View Docs → <sacro_viewer>`

ACRO: Statistical Disclosure Control
====================================

ACRO is a free and open source tool that supports the semi-automated checking of research outputs (SACRO) for privacy disclosure within secure data environments. SACRO is a framework that applies best-practice principles-based statistical disclosure control (SDC) techniques on-the-fly as researchers conduct their analysis. SACRO is designed to assist human checkers rather than seeking to replace them as with current automated rules-based approaches.

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

Semi-Automated Disclosure Checking
----------------------------------

* **Drop-in replacements** for common Python analysis commands (pandas, statsmodels, etc.) with configurable disclosure checks
* **Automated sensitivity tests**: frequency thresholds, dominance (p%, NK rules, etc.), residual degrees-of-freedom checks
* **Optional mitigations**: suppression, rounding, and more to come
* **Session management**: track, rename, comment, remove, add exceptions, and finalise reports
* **Configurable risk parameters** via YAML files
* **Generates auditable reports** in JSON or Excel

Design Principles
-----------------

* **Free and open source** under MIT (ACRO) / GPLv3 (SACRO Viewer)
* **Easy to install** via PyPI, CRAN, or GitHub; cross-platform (Linux, macOS, Windows)
* **Familiar APIs** - same function signatures as native commands: acro.crosstab mirrors pandas.crosstab, etc.
* **Comprehensive coverage** - tables, regressions, histograms, survival plots, etc.
* **Transparent & auditable** - clear reports, stored queries, designed for human-checkers
* **Configurable & extensible** - organisation-defined disclosure rules, multi-language support
* **Scalable** - lightweight, session-based, local execution

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
