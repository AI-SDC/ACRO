=============
Configuration
=============

Guide to configuring ACRO for your specific needs.

Basic Configuration
===================

ACRO expects configuration parameters to be supplied via a YAML file.
You can specify the name of your custom YAML configuration file when
initializing the ACRO session.

For example, if you have a file named `my_config.yaml` with the following content:

.. code-block:: yaml

   # my_config.yaml
   safe_threshold: 10
   safe_dof_threshold: 10
   safe_nk_n: 2
   safe_nk_k: 0.9
   # ... other parameters ...

You would then initialize your ACRO session like this:

.. code-block:: python

   import acro

   # Initialize with a custom configuration file
   session = acro.ACRO(suppress=True, config='my_config.yaml')

.. note::
   The `config` parameter in `acro.ACRO()` expects the *name of a YAML file* (e.g., 'my_config.yaml'), not a Python dictionary directly. If you wish to use a custom configuration, please save your parameters in a YAML file and provide its name.

Environment-Specific Settings
=============================

You can create different YAML files for various research environments.

For example, to define a 'high_security_config.yaml':

.. code-block:: yaml

   # high_security_config.yaml
   safe_threshold: 20
   safe_p_threshold: 0.01

And a 'standard_config.yaml':

.. code-block:: yaml

   # standard_config.yaml
   safe_threshold: 10
   safe_p_threshold: 0.1

Then, initialize your sessions accordingly:

.. code-block:: python

   import acro

   # For a high-security environment
   high_security_session = acro.ACRO(suppress=True, config='high_security_config.yaml')

   # For a standard research environment
   standard_session = acro.ACRO(suppress=True, config='standard_config.yaml')
