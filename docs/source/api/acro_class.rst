===========
ACRO Class
===========

.. currentmodule:: acro

.. autoclass:: ACRO
   :members:
   :inherited-members:
   :show-inheritance:

Method Reference
================

The ``ACRO`` class inherits analysis methods from two mixins  ``Tables`` (for tabular
and plot outputs) and ``Regression`` (for statistical models).  All methods below are
available on any ``ACRO`` instance.

Data Analysis  Tables
-----------------------

.. automethod:: ACRO.crosstab
   :no-index:
.. automethod:: ACRO.pivot_table
   :no-index:
.. automethod:: ACRO.hist
   :no-index:
.. automethod:: ACRO.pie
   :no-index:
.. automethod:: ACRO.surv_func
   :no-index:

Data Analysis  Regression
---------------------------

.. automethod:: ACRO.ols
   :no-index:
.. automethod:: ACRO.olsr
   :no-index:
.. automethod:: ACRO.logit
   :no-index:
.. automethod:: ACRO.logitr
   :no-index:
.. automethod:: ACRO.probit
   :no-index:
.. automethod:: ACRO.probitr
   :no-index:

Output Management
-----------------

.. automethod:: ACRO.finalise
   :no-index:
.. automethod:: ACRO.print_outputs
   :no-index:
.. automethod:: ACRO.remove_output
   :no-index:
.. automethod:: ACRO.rename_output
   :no-index:
.. automethod:: ACRO.custom_output
   :no-index:
.. automethod:: ACRO.add_comments
   :no-index:
.. automethod:: ACRO.add_exception
   :no-index:

Mitigation Control
------------------

.. automethod:: ACRO.enable_suppression
   :no-index:
.. automethod:: ACRO.disable_suppression
   :no-index:
.. automethod:: ACRO.enable_rounding
   :no-index:
.. automethod:: ACRO.disable_rounding
   :no-index:

Reporting
---------

.. automethod:: ACRO.show_fair_summaries
   :no-index:
