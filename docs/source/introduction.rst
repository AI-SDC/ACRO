Welcome to ACRO
==============================

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

Example
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

The main ACRO class provides the interface for all disclosure checking functionality. See the :doc:`api` documentation for complete details.

Key Parameters
--------------

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

* :py:meth:`~ACRO.crosstab` - Create cross-tabulations with disclosure checking
* :py:meth:`~ACRO.pivot_table` - Create pivot tables with disclosure checking
* :py:meth:`~ACRO.ols` - Ordinary least squares regression with disclosure checking
* :py:meth:`~ACRO.finalise` - Prepare outputs for review by data controllers

Installation
============

Install ACRO using pip:

.. code-block:: bash

   pip install acro

Quick Start
===========

1. Import ACRO and initialize
2. Load your data
3. Run analysis with automatic disclosure checking
4. Finalize outputs for review

Next Steps
==========

* :doc:`installation` - Install ACRO and set up your environment
* :doc:`user_guide` - Follow the comprehensive user guide
* :doc:`examples` - Explore example notebooks and tutorials
* :doc:`api` - Check the complete API reference