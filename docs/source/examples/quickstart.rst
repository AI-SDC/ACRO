===========
Quick Start
===========

This guide will get you up and running with ACRO in just a few minutes.

.. currentmodule:: acro

Installation
============

.. code-block:: bash

   pip install acro

Core ACRO Class
===============

.. autoclass:: ACRO
   :noindex:

Essential Methods
=================

Data Analysis
-------------

.. automethod:: ACRO.crosstab
   :noindex:

.. automethod:: ACRO.olsr
   :noindex:

Output Management
-----------------

.. automethod:: ACRO.finalise
   :noindex:

.. automethod:: ACRO.print_outputs
   :noindex:

Quick Workflow
==============

1. **Install**: ``pip install acro``
2. **Initialize**: Create ACRO session with ``suppress=True``
3. **Analyze**: Use ACRO methods for statistical analysis
4. **Review**: Check outputs with ``print_outputs()``
5. **Finalize**: Export results with ``finalise()``

Next Steps
==========

* :doc:`basic_workflow` - Learn the complete analysis workflow
* :doc:`../api` - Explore the full API reference
* :doc:`cross_tabulation` - Deep dive into cross-tabulation features