===============
Basic Workflow
===============

Complete workflow example for using ACRO in your research projects.

.. currentmodule:: acro

ACRO Session Management
=======================

Initialization
--------------

.. autoclass:: ACRO
   :noindex:

Output Management
=================

Viewing Outputs
---------------

.. automethod:: ACRO.print_outputs
   :no-index:

Finalizing Results
------------------

.. automethod:: ACRO.finalise
   :no-index:

Output Control
--------------

.. automethod:: ACRO.remove_output
   :no-index:

.. automethod:: ACRO.rename_output
   :no-index:

.. automethod:: ACRO.add_comments
   :no-index:

.. automethod:: ACRO.add_exception
   :no-index:

Custom Output Registration
--------------------------

.. automethod:: ACRO.custom_output
   :no-index:

Workflow Best Practices
=======================

1. **Initialize with suppression enabled** for production environments
2. **Use ACRO methods** for all statistical analysis
3. **Register custom outputs** for external analysis results
4. **Add meaningful comments** to outputs for reviewers
5. **Review outputs** before finalizing
6. **Use descriptive folder names** for organized output management

See Also
========

* :doc:`quickstart` - Quick introduction to ACRO
* :doc:`configuration` - Customizing ACRO settings
* :doc:`../api` - Complete API reference