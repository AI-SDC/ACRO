=========
SACRO-ML
=========

SACRO-ML is a collection of tools and resources for managing the statistical disclosure control of trained machine learning models.

Overview
========

SACRO-ML extends the SACRO framework to machine learning workflows, providing:

* Privacy-preserving model training techniques
* Automated disclosure risk assessment for ML models
* Safe model export and sharing protocols
* Integration with popular ML frameworks

Key Features
============

Model Privacy Assessment
------------------------

* Membership inference attack detection
* Model inversion risk evaluation
* Differential privacy integration

Safe Model Export
-----------------

* Automated model sanitization
* Privacy budget tracking
* Secure model serialization

Framework Integration
---------------------

* **scikit-learn** - Complete integration with sklearn pipelines
* **PyTorch** - Neural network privacy assessment
* **TensorFlow** - Deep learning model protection

Installation
============

.. code-block:: bash

   pip install sacro-ml

Quick Start
===========

.. code-block:: python

   import sacro_ml
   
   # Initialize privacy checker
   checker = sacro_ml.ModelChecker()
   
   # Assess trained model
   risk_report = checker.assess_model(trained_model, test_data)
   
   # Export safe model
   safe_model = checker.export_safe_model(trained_model)

API Reference
=============

.. note::
   Full API documentation coming soon.

Examples
========

* :doc:`examples/ml_privacy_assessment`
* :doc:`examples/safe_model_export`
* :doc:`examples/differential_privacy_training`

See Also
========

* :doc:`index` - Main ACRO documentation
* :doc:`acro_r` - R integration
* :doc:`sacro_viewer` - Output checking interface