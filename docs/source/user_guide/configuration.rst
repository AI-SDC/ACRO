=============
Configuration
=============

Comprehensive guide to configuring ACRO for your research environment and organizational policies.

Configuration Methods
=====================

YAML Configuration Files
------------------------

Primary method for persistent configuration:

.. code-block:: yaml

   # acro_config.yaml
   safe_threshold: 10
   safe_dof_threshold: 10
   safe_nk_n: 2
   safe_nk_k: 0.85
   safe_p_percent: 0.1
   check_missing_values: true
   survival_safe_threshold: 10

Runtime Parameters
------------------

You can specify the configuration file and whether to suppress unsafe outputs at runtime:

.. code-block:: python

   import acro

   # Initialize with custom parameters
   session = acro.ACRO(
       config="custom_config.yaml",  # Path to your config YAML file
       suppress=True                 # Suppress unsafe outputs
   )

Safety Parameters
=================

TRE Risk Appetite Settings
--------------------------

*These settings are typically controlled by TRE administrators and cannot be changed by researchers.*

**safe_threshold** (default: 10)
   Minimum number of observations required in table cells

**safe_dof_threshold** (default: 10)
   Minimum degrees of freedom for statistical models

**safe_nk_n** (default: 2)
   Number of largest contributors for NK dominance rule

**safe_nk_k** (default: 0.85)
   Percentage threshold for NK dominance rule

**safe_p_percent** (default: 0.1)
   P-percent rule threshold for concentration

**check_missing_values** (default: true)
   Include missing values in safety calculations

**survival_safe_threshold** (default: 10)
   Minimum observations for survival analysis outputs

**zeros_are_disclosive** (default: true)
   Whether zero values are considered disclosive. TREs can set this to false for datasets where class disclosure is not relevant

Behavioral Settings
-------------------

*These settings can be controlled by researchers to choose how they want to mitigate risk.*

**suppress** (default: false)
   Whether to suppress unsafe outputs automatically.

Configuration Precedence
========================

Settings are applied in order of precedence:

1. Runtime method parameters (where supported)
2. Configuration file settings
3. Default values

Best Practices
==============

Version Control
---------------

* Store configuration files in version control
* Use meaningful commit messages for config changes

Documentation
-------------

* Document all custom settings and their rationale
* Maintain configuration change logs
* Include configuration in analysis documentation

Testing
-------

* Test configuration changes with sample data
* Validate against organizational policies
