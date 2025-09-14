==================
Summary Statistics
==================

Computing safe summary statistics with ACRO.

.. currentmodule:: acro

Tabular Summary Methods
=======================

Pivot Tables
------------

.. automethod:: ACRO.pivot_table
   :no-index:

Cross-tabulations
-----------------

.. automethod:: ACRO.crosstab
   :no-index:

Output Management for Custom Statistics
=======================================

Custom Output Registration
--------------------------

.. automethod:: ACRO.custom_output
   :no-index:

Output Comments
---------------

.. automethod:: ACRO.add_comments
   :no-index:

Working with External Statistics
================================

ACRO doesn't have a built-in describe() method, but you can safely work with pandas statistics:

1. Generate statistics using pandas (e.g., ``data.describe()``)
2. Save results to file
3. Register with ACRO using ``custom_output()``
4. Add descriptive comments using ``add_comments()``

This approach ensures all outputs are tracked and reviewed through ACRO's disclosure control workflow.

See Also
========

* :doc:`cross_tabulation` - Detailed cross-tabulation examples
* :doc:`../api` - Complete API reference