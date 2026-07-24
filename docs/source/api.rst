=============
API Reference
=============

This section provides detailed documentation for all ACRO classes, functions, and modules.

.. currentmodule:: acro

Core Classes
============

.. toctree::
   :maxdepth: 2
   :caption: ACRO Classes

   api/acro_class
   api/records_class

ACRO Class
----------

The main entry point.  Inherits from ``Tables`` and ``Regression`` mixins which provide
the analysis methods.

.. autoclass:: acro.ACRO
   :members:
   :inherited-members:
   :show-inheritance:
   :no-index:

Ontology-Driven Checking Classes
=================================

The classes below form ACRO's internal disclosure-checking pipeline.  Most users will
never instantiate these directly  they are created and managed by the ``ACRO`` class.
They are documented here for developers and TRE administrators.

SDCChecks
----------

.. autoclass:: acro.sdcchecks.SDCChecks
   :members:
   :show-inheritance:
   :no-index:

SDCEvidence
-----------

.. autoclass:: acro.sdcchecks.SDCEvidence
   :members:
   :show-inheritance:
   :no-index:

ChecksResults
--------------

.. autoclass:: acro.sdcchecks.ChecksResults
   :members:
   :show-inheritance:
   :no-index:

ManyChecksResults
-----------------

.. autoclass:: acro.sdcchecks.ManyChecksResults
   :members:
   :show-inheritance:
   :no-index:

TableModelDetails
-----------------

.. autoclass:: acro.tablemodeldetails.TableModelDetails
   :members:
   :show-inheritance:
   :no-index:

Record Management
=================

Record Classes
--------------

.. autoclass:: acro.record.Records
   :members:
   :show-inheritance:
   :no-index:

Record Module
-------------

.. include:: record.rst

Utilities
=========

Helper Functions
----------------

.. automodule:: acro.utils
   :members:
   :show-inheritance:
   :no-index:

Table Utilities
---------------

.. automodule:: acro.table_utils
   :members:
   :show-inheritance:
   :no-index:

Function Reference by Category
==============================

Output Management
-----------------

* ``finalise()``  Prepare outputs for review
* ``remove_output()``  Remove specific output
* ``print_outputs()``  Display current outputs
* ``custom_output()``  Add custom output
* ``rename_output()``  Rename an output
* ``add_comments()``  Add comments to output
* ``add_exception()``  Add exception request

Mitigation Control
------------------

* ``enable_suppression()``  Switch to suppression mode
* ``disable_suppression()``  Disable suppression
* ``enable_rounding(base)``  Switch to rounding mode
* ``disable_rounding()``  Disable rounding

Common Parameters
=================

Many ACRO methods share common parameters:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - ``suppress``
     - bool
     - Whether to suppress potentially disclosive outputs automatically.
   * - ``federated``
     - bool
     - Whether to run in federated mode (evidence sent to a trusted aggregator).
   * - ``show_suppressed``
     - bool
     - Whether to display suppressed values in the output table.
   * - ``safe_threshold``
     - int
     - Minimum cell count threshold (TRE-controlled; set in YAML config).
   * - ``safe_dof_threshold``
     - int
     - Minimum degrees of freedom for statistical models.
   * - ``safe_nk_n``
     - int
     - *n* in the NK dominance rule.
   * - ``safe_nk_k``
     - float
     - *k* (proportion) in the NK dominance rule.
   * - ``safe_pratio_p``
     - float
     - P-ratio threshold for dominance checking.

Configuration
=============

ACRO uses YAML configuration files to set safety parameters:

.. code-block:: python

   # Initialise with default config
   session = acro.ACRO()

   # Initialise with suppress mode on
   session = acro.ACRO(suppress=True)

   # Initialise with a custom config file
   session = acro.ACRO(config="custom.yaml")

Custom Configuration
--------------------

Create a custom YAML file for your TRE:

.. code-block:: yaml

   # custom.yaml
   safe_threshold: 10
   safe_dof_threshold: 10
   safe_nk_n: 2
   safe_nk_k: 0.9
   safe_pratio_p: 0.1
   check_missing_values: false
   zeros_are_disclosive: true
   safe_round_base: 5
   federated: false
   blocked_extensions:
     - .svg
     - .gph

Version Information
===================

.. code-block:: python

   import acro
   from acro.version import __version__
   print(__version__)

See Also
========

* :doc:`user_guide/architecture`  Detailed technical architecture reference
* :doc:`examples`  Usage examples and tutorials
* :doc:`installation`  Installation instructions
* :doc:`introduction`  Getting started guide
