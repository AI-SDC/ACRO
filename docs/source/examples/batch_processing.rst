================
Batch Processing
================

Processing multiple analyses efficiently with ACRO.

.. currentmodule:: acro

Batch Output Management
=======================

Output Tracking
---------------

.. automethod:: ACRO.print_outputs
   :no-index:

Batch Finalization
------------------

.. automethod:: ACRO.finalise
   :no-index:

Output Organization
-------------------

.. automethod:: ACRO.rename_output
   :no-index:

.. automethod:: ACRO.add_comments
   :no-index:

Batch Processing Strategies
===========================

For large-scale analysis workflows:

1. **Single Session**: Use one ACRO session for related analyses
2. **Organized Naming**: Use ``rename_output()`` for clear identification
3. **Descriptive Comments**: Add comments to each output for context
4. **Batch Finalization**: Export all results together with ``finalise()``

Utility Functions
=================

External File Processing
------------------------

.. autofunction:: add_to_acro

This function helps integrate existing analysis results into ACRO's disclosure control workflow.

See Also
========

* :doc:`basic_workflow` - Standard workflow patterns
* :doc:`../api` - Complete API reference