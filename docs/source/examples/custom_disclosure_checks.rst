========================
Custom Disclosure Checks
========================

Advanced configuration of disclosure control parameters.

.. currentmodule:: acro

Configuration Management
========================

ACRO Configuration
------------------

.. autoclass:: ACRO
   :noindex:

The ACRO class accepts configuration parameters that control disclosure checking behavior. Configuration is loaded from YAML files in the package.

Advanced Output Control
=======================

Exception Handling
------------------

.. automethod:: ACRO.add_exception
   :no-index:

Custom Comments
---------------

.. automethod:: ACRO.add_comments
   :no-index:

Configuration Parameters
========================

ACRO uses several key parameters for disclosure control:

* ``safe_threshold`` - Minimum cell count threshold
* ``safe_dof_threshold`` - Minimum degrees of freedom for models
* ``safe_nk_n`` - Number of top contributors for nk-dominance rule
* ``safe_nk_k`` - Threshold for nk-dominance rule
* ``safe_pratio_p`` - P-ratio threshold for disclosure

These are configured in YAML files and can be customized for different research environments.

See Also
========

* :doc:`configuration` - Basic configuration guide
* :doc:`../api` - Complete API reference