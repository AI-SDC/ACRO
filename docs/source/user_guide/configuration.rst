=============
Configuration
=============

Comprehensive guide to configuring ACRO for your research environment and organisational policies.

Configuration Methods
=====================

YAML Configuration Files
------------------------

The primary method for persistent configuration is a YAML file.  ACRO ships with a
``default.yaml`` that is used automatically when no custom file is specified.

.. code-block:: yaml

   # acro_config.yaml
   safe_threshold: 10
   safe_dof_threshold: 10
   safe_nk_n: 2
   safe_nk_k: 0.9
   safe_pratio_p: 0.1
   check_missing_values: false
   survival_safe_threshold: 10
   zeros_are_disclosive: true
   safe_round_base: 5
   federated: false
   blocked_extensions:
     - .svg
     - .gph

Runtime Parameters
------------------

Specify your configuration file and mitigation strategy at session creation:

.. code-block:: python

   import acro

   # Use the defaults
   session = acro.ACRO()

   # Enable automatic suppression
   session = acro.ACRO(suppress=True)

   # Enable rounding to the nearest 5
   session = acro.ACRO()
   session.enable_rounding(base=5)

   # Federated mode (send evidence to a trusted aggregator)
   session = acro.ACRO(federated=True)

   # Custom config file
   session = acro.ACRO(config="my_tre_config.yaml", suppress=True)

.. note::
   The ``config`` parameter expects the **name of a YAML file** (e.g. ``"my_config.yaml"``),
   not a Python dictionary.  Save your parameters in a YAML file and provide its filename.

Switching Mitigation at Runtime
---------------------------------

You can change the mitigation strategy after session creation:

.. code-block:: python

   session = acro.ACRO()

   session.enable_suppression()       # switch to suppression mode
   session.disable_suppression()      # switch back to no-mitigation mode

   session.enable_rounding(base=5)    # switch to rounding mode
   session.disable_rounding()         # switch back to no-mitigation mode

Suppression and rounding are mutually exclusive  enabling one automatically disables the other.

Safety Parameters
=================

TRE Risk Appetite Settings
--------------------------

*These settings are typically controlled by TRE administrators and should not be changed
by researchers.*

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Default
     - Description
   * - ``safe_threshold``
     - 10
     - Minimum number of observations required in a table cell.
   * - ``safe_dof_threshold``
     - 10
     - Minimum residual degrees of freedom for statistical models.
   * - ``safe_nk_n``
     - 2
     - *n* in the NK dominance rule: the top *n* contributors must not
       account for more than ``safe_nk_k`` of a cell's total.
   * - ``safe_nk_k``
     - 0.9
     - *k* in the NK dominance rule (proportion, 0–1).
   * - ``safe_pratio_p``
     - 0.1
     - P-ratio threshold  the remaining contributors must account for
       at least this fraction of the largest contributor's value.
   * - ``check_missing_values``
     - false
     - Whether to flag cells that contain missing values.
   * - ``survival_safe_threshold``
     - 10
     - Minimum observations at risk for survival analysis outputs.
   * - ``zeros_are_disclosive``
     - true
     - Whether zero-count cells are treated as disclosive.  Set to
       ``false`` for datasets where class disclosure is not a concern.
       Also controls whether empty histogram bins are excluded from the
       threshold check.
   * - ``safe_round_base``
     - 5
     - Default rounding base used by the ``round`` mitigation strategy.
   * - ``federated``
     - false
     - Whether to run in federated mode (evidence sent to a trusted
       aggregator instead of running checks locally).
   * - ``blocked_extensions``
     - ``[".svg", ".gph"]``
     - File extensions that ACRO will refuse to write (e.g. formats that
       may embed raw data).

Researcher-Controlled Settings
--------------------------------

*These settings can be changed by researchers to choose how risk is mitigated.*

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter / Method
     - Default
     - Description
   * - ``suppress`` (constructor)
     - ``False``
     - Pass ``True`` to have unsafe cells suppressed (replaced with NaN)
       automatically.
   * - ``enable_rounding(base)``
     - 
     - Switch to rounding mode.  ``base`` must be a positive integer.
   * - ``enable_suppression()``
     - 
     - Switch to suppression mode.
   * - ``disable_suppression()``
     - 
     - Remove suppression without enabling rounding.
   * - ``disable_rounding()``
     - 
     - Remove rounding without enabling suppression.

How the Ontology Knowledge Base Is Generated
=============================================

ACRO's checking rules are defined by the `StatbarnsSDC ontology <https://w3id.org/statbarnsdc>`_.
Because TREs may not have internet access, the knowledge is pre-compiled into four JSON files
that ship with every release:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - File
     - Contents
   * - ``analyses.json``
     - Maps analysis type names to the *statbarn* (SDC category) they belong to.
   * - ``statbarns.json``
     - Maps each statbarn to the risks associated with it.
   * - ``risks.json``
     - Maps each risk to the checks that detect it and mitigations that address it.
   * - ``checks.json``
     - Maps each check to the evidence it requires.

These files are regenerated by ``acro/ontology_handler.py`` before each release.
**Researchers do not need to run this script**  the generated files are included
in the ``acro`` package.

If a TRE needs to customise the knowledge base (for example, to add a locally
defined statbarn), the administrator can run ``ontology_handler.py`` against a
modified ontology and replace the JSON files in the installation.

Configuration Precedence
========================

Settings are applied in the following order (highest priority first):

1. Methods called on an active session (e.g. ``enable_rounding()``).
2. Constructor arguments (``suppress=True``, ``federated=True``).
3. Settings in the YAML configuration file.
4. ACRO's built-in defaults (``default.yaml``).

Best Practices
==============

Version Control
---------------

* Store your configuration YAML in version control alongside your analysis scripts.
* Use meaningful commit messages when changing thresholds.
* Keep a ``README`` explaining any deviations from the TRE's standard config.

Documentation
-------------

* Record the rationale for any non-default threshold in your analysis plan.
* Include the configuration file name in your output-checker submission.

Testing
-------

* Test new configuration values with a small synthetic dataset before running
  on sensitive data.
* Verify that the expected cells are flagged or suppressed as intended.
