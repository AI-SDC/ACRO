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

.. autoclass:: acro.ACRO
   :members:
   :inherited-members:
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

Function Reference by Category
==============================

Output Management
-----------------

* ``finalise()`` - Prepare outputs for review
* ``remove_output()`` - Remove specific output
* ``print_outputs()`` - Display current outputs
* ``custom_output()`` - Add custom output
* ``rename_output()`` - Rename an output
* ``add_comments()`` - Add comments to output
* ``add_exception()`` - Add exception request

Method Parameters
=================

Common Parameters
-----------------

Many ACRO methods share common parameters:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - ``suppress``
     - bool
     - Whether to suppress potentially disclosive outputs
   * - ``show_suppressed``
     - bool
     - Whether to display suppressed values in output
   * - ``safe_threshold``
     - int
     - Minimum cell count threshold for safety
   * - ``safe_dof_threshold``
     - int
     - Minimum degrees of freedom for statistical models
   * - ``safe_nk_n``
     - int
     - Minimum number of observations for nk-dominance rule
   * - ``safe_nk_k``
     - float
     - Threshold for nk-dominance rule (0-1)
   * - ``safe_p_threshold``
     - float
     - P-value threshold for statistical significance

Return Types
============

Output Objects
--------------

Most ACRO functions return specialized output objects that contain:

* **Original Result**: The unmodified analysis result
* **Safe Result**: The disclosure-controlled version
* **Disclosure Checks**: Details of applied safety checks
* **Metadata**: Information about the analysis and safety measures

.. code-block:: python

   # Example return object structure
   result = acro.crosstab(df.col1, df.col2)

   # Access components
   print(result.output)          # Safe output for display
   print(result.disclosure_checks)  # Applied safety checks
   print(result.metadata)        # Analysis metadata

Return Types
============

Output Objects
--------------

ACRO functions return results that are automatically checked for disclosure risks:

.. code-block:: python

   import acro

   # Initialize ACRO
   session = acro.ACRO(suppress=True)

   # Results are automatically checked
   result = session.crosstab(df.col1, df.col2)

   # View outputs
   session.print_outputs()

   # Finalize for review
   session.finalise("outputs/")

Version Information
===================

.. code-block:: python

   import acro
   from acro.version import __version__
   print(__version__)

Compatibility
=============

Python Version Support
----------------------

ACRO supports Python 3.9 and later versions.

Dependency Requirements
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Package
     - Minimum Version
     - Purpose
   * - pandas
     - 1.5.0
     - Data manipulation and analysis
   * - numpy
     - 1.21.0
     - Numerical computing
   * - statsmodels
     - 0.13.0
     - Statistical modeling
   * - openpyxl
     - 3.0.0
     - Excel file support
   * - pyyaml
     - 5.4.0
     - Configuration file handling

Configuration
=============

ACRO uses YAML configuration files to set safety parameters:

.. code-block:: python

   # Initialize with default config
   session = acro.ACRO(config="default", suppress=True)

   # Configuration is loaded from default.yaml
   print(session.config)

Custom Configuration
--------------------

Create custom YAML files for different environments:

.. code-block:: yaml

   # custom.yaml
   safe_threshold: 10
   safe_nk_n: 2
   safe_nk_k: 0.9
   check_missing_values: true
   zeros_are_disclosive: false

See Also
========

* :doc:`examples` - Usage examples and tutorials
* :doc:`installation` - Installation instructions
* :doc:`introduction` - Getting started guide
