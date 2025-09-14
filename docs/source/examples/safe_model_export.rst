=================
Safe Model Export
=================

Exporting machine learning models safely using SACRO-ML.

.. note::
   This section covers SACRO-ML functionality. For ACRO-specific examples, see :doc:`basic_workflow` and :doc:`cross_tabulation`.

Overview
========

Safe model export ensures that trained machine learning models can be shared without exposing sensitive information from the training data.

Key Components
==============

Model Sanitization
------------------

Techniques for removing potentially sensitive information from model parameters:

* Parameter noise injection
* Model compression techniques
* Gradient sanitization
* Weight pruning strategies

Privacy Budget Tracking
-----------------------

Systematic tracking of privacy expenditure during model training and export:

* Differential privacy budget management
* Privacy loss accounting
* Multi-stage privacy tracking
* Composition theorem applications

Secure Model Serialization
---------------------------

Safe methods for saving and sharing trained models:

* Encrypted model storage
* Secure model format specifications
* Access control mechanisms
* Audit trail generation

Safe Model Sharing Protocols
-----------------------------

Established procedures for distributing models safely:

* Model validation workflows
* Privacy compliance checking
* Secure transfer protocols
* Usage monitoring systems

SACRO-ML Integration
====================

SACRO-ML provides automated tools for safe model export that integrate with:

* **PyTorch** - Neural network privacy assessment
* **TensorFlow** - Deep learning model protection  
* **scikit-learn** - Traditional ML model safety
* **Hugging Face** - Transformer model privacy

Installation and Usage
======================

.. code-block:: bash

   pip install sacro-ml

For detailed implementation examples and API documentation, see the :doc:`../sacro_ml` documentation.

Best Practices
==============

1. **Assess Privacy Risks** before model export
2. **Apply Appropriate Sanitization** based on risk assessment
3. **Track Privacy Budget** throughout the process
4. **Validate Model Safety** before distribution
5. **Monitor Model Usage** after deployment

See Also
========

* :doc:`../sacro_ml` - Complete SACRO-ML documentation
* :doc:`ml_privacy_assessment` - Privacy risk assessment
* :doc:`differential_privacy_training` - DP training methods