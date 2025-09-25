=============
Configuration
=============

Guide to configuring ACRO for your specific needs.

Basic Configuration
===================

.. code-block:: python

   import acro

   # Custom configuration
   config = {
       'safe_threshold': 10,
       'safe_dof_threshold': 10,
       'safe_nk_n': 2,
       'safe_nk_k': 0.9
   }

   session = acro.ACRO(suppress=True, config=config)

Environment-Specific Settings
=============================

Configuration examples for different research environments.

.. code-block:: python

   # High-security environment
   high_security_config = {
       'safe_threshold': 20,
       'safe_p_threshold': 0.01
   }

   # Standard research environment
   standard_config = {
       'safe_threshold': 10,
       'safe_p_threshold': 0.1
   }
