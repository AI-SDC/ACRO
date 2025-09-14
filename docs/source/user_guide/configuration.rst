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

Override configuration at runtime:

.. code-block:: python

   import acro
   
   # Initialize with custom parameters
   session = acro.ACRO(
       config="custom_config.yaml",
       suppress=True,
       safe_threshold=15
   )

Environment Variables
---------------------

System-level configuration:

.. code-block:: bash

   export ACRO_CONFIG_PATH="/path/to/config.yaml"
   export ACRO_SAFE_THRESHOLD=10
   export ACRO_SUPPRESS=true

Safety Parameters
=================

Threshold Settings
------------------

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

Behavioral Settings
-------------------

**suppress** (default: false)
   Whether to suppress unsafe outputs automatically

**check_missing_values** (default: true)
   Include missing values in safety calculations

**survival_safe_threshold** (default: 10)
   Minimum observations for survival analysis outputs

Output Settings
===============

File Management
---------------

**output_dir** (default: "outputs")
   Directory for saved outputs and reports

**filename_format** (default: "{timestamp}_{method}_{description}")
   Template for output filenames

**save_intermediate** (default: false)
   Save intermediate analysis steps

Report Generation
-----------------

**create_report** (default: true)
   Generate summary reports automatically

**report_format** (default: "html")
   Output format for reports (html, pdf, txt)

**include_warnings** (default: true)
   Include disclosure warnings in reports

Advanced Configuration
======================

Custom Disclosure Rules
-----------------------

Define organization-specific rules:

.. code-block:: yaml

   custom_rules:
     - name: "financial_data_rule"
       condition: "column_contains('income', 'salary')"
       threshold: 20
       message: "Financial data requires higher threshold"
     
     - name: "geographic_rule"
       condition: "geographic_level == 'postcode'"
       threshold: 50
       message: "Postcode-level data needs special protection"

Integration Settings
--------------------

**tre_integration** (default: false)
   Enable Trusted Research Environment features

**airlock_path** (default: null)
   Path to TRE airlock directory

**approval_workflow** (default: false)
   Enable output approval workflows

**multi_user** (default: false)
   Support for shared analysis environments

Policy Templates
================

Organizational Policies
-----------------------

Create reusable policy configurations:

.. code-block:: yaml

   # policy_strict.yaml
   extends: "base_config.yaml"
   safe_threshold: 20
   safe_nk_k: 0.9
   suppress: true
   require_approval: true

   # policy_research.yaml  
   extends: "base_config.yaml"
   safe_threshold: 10
   suppress: false
   create_report: true

Domain-Specific Settings
------------------------

**Healthcare Data**

.. code-block:: yaml

   healthcare_policy:
     safe_threshold: 15
     check_rare_diseases: true
     hipaa_compliance: true
     phi_detection: true

**Financial Data**

.. code-block:: yaml

   financial_policy:
     safe_threshold: 25
     check_high_earners: true
     pci_compliance: true
     transaction_limits: true

Configuration Validation
========================

Schema Validation
-----------------

ACRO validates configuration against schema:

.. code-block:: python

   # Validate configuration file
   acro.validate_config("my_config.yaml")
   
   # Check current session configuration
   session.validate_configuration()

Testing Configuration
---------------------

Test with sample data:

.. code-block:: python

   # Test configuration with dummy data
   test_session = acro.ACRO(config="test_config.yaml")
   test_session.test_configuration(sample_data)

Environment-Specific Setup
==========================

Development Environment
-----------------------

.. code-block:: yaml

   # dev_config.yaml
   safe_threshold: 5
   suppress: false
   create_report: true
   save_intermediate: true
   debug_mode: true

Production Environment
----------------------

.. code-block:: yaml

   # prod_config.yaml
   safe_threshold: 10
   suppress: true
   create_report: true
   audit_logging: true
   strict_validation: true

Testing Environment
-------------------

.. code-block:: yaml

   # test_config.yaml
   safe_threshold: 3
   suppress: false
   mock_data: true
   validation_only: true

Troubleshooting
===============

Common Issues
-------------

**Configuration not loading**
   - Check file path and permissions
   - Validate YAML syntax
   - Verify environment variables

**Unexpected behavior**
   - Review parameter precedence
   - Check for conflicting settings
   - Validate against schema

**Performance issues**
   - Adjust threshold settings
   - Disable unnecessary features
   - Optimize file I/O settings

Configuration Precedence
------------------------

Settings are applied in order of precedence:

1. Runtime method parameters
2. Session initialization parameters  
3. Environment variables
4. Configuration file settings
5. Default values

Best Practices
==============

Version Control
---------------

* Store configuration files in version control
* Use meaningful commit messages for config changes
* Tag configuration versions with releases

Documentation
-------------

* Document all custom settings and their rationale
* Maintain configuration change logs
* Include configuration in analysis documentation

Testing
-------

* Test configuration changes with sample data
* Validate against organizational policies
* Monitor performance impact of changes