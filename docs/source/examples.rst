========
Examples
========

This section provides comprehensive examples and tutorials for using the ACRO family of tools.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   examples/quickstart
   examples/basic_workflow
   examples/configuration

.. toctree::
   :maxdepth: 2
   :caption: Data Analysis Examples

   examples/cross_tabulation
   examples/statistical_modeling
   examples/data_visualization
   examples/summary_statistics

.. toctree::
   :maxdepth: 2
   :caption: Advanced Usage

   examples/custom_disclosure_checks
   examples/batch_processing
   examples/integration_workflows

.. toctree::
   :maxdepth: 2
   :caption: Language-Specific Examples

   examples/python_notebooks
   examples/r_workflows
   examples/stata_integration

.. toctree::
   :maxdepth: 2
   :caption: Machine Learning

   examples/ml_privacy_assessment
   examples/safe_model_export
   examples/differential_privacy_training

.. toctree::
   :maxdepth: 2
   :caption: Output Checking

   examples/sacro_viewer_tutorial
   examples/reviewer_workflows
   examples/tre_integration





Interactive Notebooks
=====================

Python Jupyter Notebooks
-------------------------

* `Basic ACRO Tutorial <_static/test.nb.html>`_ - Introduction to ACRO with the charities dataset
* `Advanced Analysis <_static/test-nursery.nb.html>`_ - Complex analysis with the nursery dataset

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

**Usage**: Perfect for machine learning and classification examples

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

3. **Machine Learning Projects**
   
   * Privacy-preserving model training
   * Safe model evaluation and comparison
   * Secure model deployment

TRE Integration Examples
------------------------

1. **Airlock Integration**
   
   * Automated output submission
   * Integration with approval workflows
   * Secure file transfer protocols

2. **Multi-user Environments**
   
   * Shared configuration management
   * Collaborative analysis workflows
   * Output tracking and versioning

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