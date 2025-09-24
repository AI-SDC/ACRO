=======================
ML Privacy Assessment
=======================

Assessing privacy risks in machine learning models using SACRO-ML.

.. note::
   This section covers SACRO-ML functionality. For ACRO-specific examples, see :doc:`cross_tabulation` and :doc:`statistical_modeling`.

Overview
========

SACRO-ML provides tools for assessing privacy risks in machine learning models, including:

* Membership inference attack detection
* Model inversion risk evaluation  
* Differential privacy integration
* Safe model evaluation metrics

Key Concepts
============

Membership Inference Attacks
----------------------------

Attacks that attempt to determine if a specific data point was used in training a model.

Model Inversion Attacks
-----------------------

Attacks that attempt to reconstruct training data from model parameters or outputs.

Differential Privacy
--------------------

Mathematical framework for quantifying and limiting privacy loss in machine learning.

SACRO-ML Integration
====================

SACRO-ML extends the SACRO framework to machine learning workflows by providing:

* Privacy risk assessment tools
* Safe model export protocols
* Integration with popular ML frameworks
* Automated privacy budget tracking

Installation
============

.. code-block:: bash

   pip install sacro-ml

For detailed installation and usage instructions, see the :doc:`../sacro_ml` documentation.

See Also
========

* :doc:`../sacro_ml` - Complete SACRO-ML documentation
* :doc:`safe_model_export` - Safe model export procedures
* :doc:`differential_privacy_training` - DP training techniques