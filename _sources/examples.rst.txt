========
Examples
========

This section provides comprehensive examples and tutorials for using the ACRO family of tools.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   examples/quickstart
   examples/configuration
   notebook_examples





Interactive Notebooks
=====================

Python Jupyter Notebooks
-------------------------

* :doc:`../notebooks/test` - Introduction to ACRO with the charities dataset
* :doc:`../notebooks/test-nursery` - Complex analysis with the nursery dataset

R Notebooks
-----------

* `ACRO-R Quickstart <https://ai-sdc.github.io/ACRO/_static/test.nb.html>`_ - Getting started with ACRO in R
* `Statistical Modeling in R <https://ai-sdc.github.io/ACRO/_static/test-nursery.nb.html>`_ - Advanced R workflows

Video Tutorials
===============

* `ACRO Installation and Setup <https://drive.google.com/drive/folders/1z5zKuZdiNth0c7CLBt3vDEyhGwSIocw_>`_
* `Basic Data Analysis Workflow <https://drive.google.com/drive/folders/1z5zKuZdiNth0c7CLBt3vDEyhGwSIocw_>`_
* `Output Checking with SACRO-Viewer <https://drive.google.com/drive/folders/1z5zKuZdiNth0c7CLBt3vDEyhGwSIocw_>`_

Example Datasets
================

The following datasets are available for testing and learning:

Charities Dataset
-----------------

A synthetic dataset containing information about charitable organizations, including:

* Organization details (name, type, region)
* Financial information (income, expenditure)
* Activity classifications

**Usage**: Ideal for learning cross-tabulation and basic statistical analysis

Nursery Dataset
---------------

A classification dataset for nursery school applications, featuring:

* Categorical variables (parents, has_nurs, form, children, housing, finance, social, health)
* Target variable (spec_prior, priority, not_recom)

**Usage**: Perfect for statistical modeling and regression examples

Sample Code Repository
======================

All example code is available in the `ACRO Examples Repository <https://github.com/AI-SDC/ACRO-Examples>`_.

.. code-block:: bash

   # Clone examples repository
   git clone https://github.com/AI-SDC/ACRO-Examples.git
   cd ACRO-Examples

   # Install requirements
   pip install -r requirements.txt

   # Run Jupyter notebooks
   jupyter notebook

Common Use Cases
================

Research Workflow Examples
--------------------------

1. **Exploratory Data Analysis**

   * Safe data exploration and summarization
   * Identifying patterns while protecting privacy
   * Generating publication-ready tables

2. **Statistical Modeling**

   * Regression analysis with disclosure control
   * Model comparison and selection
   * Coefficient interpretation and reporting

3. **Advanced Statistical Analysis**

   * Complex regression modeling
   * Survival analysis with disclosure control
   * Custom statistical procedures

TRE Integration
---------------

ACRO integrates with Trusted Research Environments (TREs) to provide:

* **Automated output submission** to approval workflows
* **Integration with existing TRE systems** and security protocols
* **Multi-user support** with shared configuration management
* **Audit trails** for compliance and tracking

Best Practices Examples
-----------------------

1. **Configuration Management**

   * Environment-specific settings
   * Threshold customization
   * Policy compliance

2. **Quality Assurance**

   * Reproducible analysis workflows
   * Version control integration
   * Documentation standards

Getting Help
============

If you need help with any examples:

* Check the :doc:`api` for detailed function documentation
* Visit our `GitHub Issues <https://github.com/AI-SDC/ACRO/issues>`_ page
* Join our community discussions
* Contact support: acro-support@ai-sdc.org

Contributing Examples
=====================

We welcome contributions of new examples and tutorials:

1. Fork the `ACRO Examples Repository <https://github.com/AI-SDC/ACRO-Examples>`_
2. Create a new example following our template
3. Test your example thoroughly
4. Submit a pull request with documentation

Example Template
----------------

.. code-block:: python

   """
   Example Title: Brief Description

   This example demonstrates [specific functionality].

   Requirements:
   - acro >= 0.4.8
   - pandas >= 1.5.0

   Dataset: [dataset name and source]
   Difficulty: [Beginner/Intermediate/Advanced]
   """

   import acro
   import pandas as pd

   # Example code here...

See Also
========

* :doc:`installation` - Installation instructions
* :doc:`api` - Complete API reference
* :doc:`introduction` - Getting started guide
