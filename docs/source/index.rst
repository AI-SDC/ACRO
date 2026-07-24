.. raw:: html

   <div style="text-align: left; margin: 20px 0;">
      <img src="./_static/SACRO_Logo_final.png" alt="SACRO Logo" width="100" style="background: transparent !important; border: none;" />
   </div>

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
        :link: http://sacro-ml.sacro-tools.org
        :link-type: url
        :shadow: md
        :class-header: bg-info

        **Machine Learning Privacy Tools**

        Collection of tools and resources for managing the statistical disclosure control of trained machine learning models.

        +++

        :bdg-info:`ML Privacy` :doc:`Learn More → <sacro_ml>`

.. grid:: 2

    .. grid-item-card:: ACRO-R
        :link: http://acro-r.sacro-tools.org
        :link-type: url
        :shadow: md
        :class-header: bg-success

        **R Package Integration**

        R-language interface for the Python ACRO library, providing familiar R syntax for statistical disclosure control.

        +++

        :bdg-success:`R Integration` :doc:`Explore → <acro_r>`

    .. grid-item-card:: SACRO-Viewer
        :link: http://sacro-viewer.sacro-tools.org
        :link-type: url
        :shadow: md
        :class-header: bg-info


        **Graphical User Interface**

        A graphical user interface for fast, secure and effective output checking, which can work in any TRE (Trusted Research Environment).

        +++

        :bdg-warning:`GUI Tool` :doc:`View Docs → <sacro_viewer>`

ACRO: Statistical Disclosure Control
====================================

ACRO is a free and open source tool that supports the semi-automated checking of research outputs (SACRO) for privacy disclosure within secure data environments. SACRO is a framework that applies best-practice principles-based statistical disclosure control (SDC) techniques on-the-fly as researchers conduct their analysis. SACRO is designed to assist human checkers rather than seeking to replace them as with current automated rules-based approaches.

.. note::
   **New in v0.4.12  Ontology-Driven Architecture:** ACRO's checking rules are now
   driven by the `StatbarnsSDC ontology <https://w3id.org/statbarnsdc>`_, compiled into
   JSON lookup tables bundled with the package.  For a beginner-friendly explanation see
   :doc:`introduction`, or :doc:`user_guide/architecture` for the full technical reference.

What is ACRO?
=============

ACRO implements a principles-based statistical disclosure control (SDC) methodology that:

* Automatically identifies potentially disclosive outputs
* Applies optional disclosure mitigation strategies (suppression or rounding)
* Reports *why* each check was applied, grounded in a formal ontology
* Produces auditable summary documents for output checkers


Core Features
=============

Semi-Automated Disclosure Checking
----------------------------------

* **Drop-in replacements** for common Python analysis commands (pandas, statsmodels, etc.) with configurable disclosure checks
* **Automated sensitivity tests**: frequency thresholds, dominance (p%, NK rules), residual degrees-of-freedom checks, missing-value checks
* **Ontology-driven rule engine**: the checks that apply to each analysis type are read from ``analyses.json``, ``statbarns.json``, ``risks.json``, and ``checks.json``  no hard-coded logic
* **Optional mitigations**: suppression (records redacted, table rerun) or rounding (to nearest configurable multiple)
* **Session management**: track, rename, comment, remove, add exceptions, and finalise reports
* **Configurable risk parameters** via YAML files
* **Generates auditable reports** in JSON or Excel

Design Principles
-----------------

* **Free and open source** under MIT (ACRO) / GPLv3 (SACRO Viewer)
* **Easy to install** via PyPI, CRAN, or GitHub; cross-platform (Linux, macOS, Windows)
* **Familiar APIs**  same function signatures as native commands: ``acro.crosstab`` mirrors ``pandas.crosstab``
* **Comprehensive coverage**  tables, regressions, histograms, survival plots
* **Transparent & auditable**  clear FAIR reports, stored queries, designed for human checkers
* **Configurable & extensible**  organisation-defined disclosure rules, multi-language support
* **Offline-ready**  all SDC knowledge is bundled as JSON; no internet access required inside a TRE

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

* **Making tables**  e.g. :py:meth:`~acro.ACRO.crosstab`
* **Regression analysis**  e.g. :py:meth:`~acro.ACRO.ols`
* **Making plots**  e.g. :py:meth:`~acro.ACRO.hist`
* **Managing a research session**  e.g. :py:meth:`~acro.ACRO.finalise`

Community and Support
=====================

.. grid:: 2

    .. grid-item-card:: Get Help
        :class-header: bg-light

        * `GitHub Issues <https://github.com/AI-SDC/ACRO/issues>`_
        * `Discussion Forum <https://github.com/AI-SDC/ACRO/discussions>`_
        * Email: sacro.contact@uwe.ac.uk

    .. grid-item-card:: Contribute
        :class-header: bg-light

        * `Contributing Guide <https://github.com/AI-SDC/ACRO/blob/main/CONTRIBUTING.md>`_
        * `Source Code <https://github.com/AI-SDC/ACRO>`_
        * `Report Issues <https://github.com/AI-SDC/ACRO/issues/new>`_

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
