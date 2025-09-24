=============================
Differential Privacy Training
=============================

Training machine learning models with differential privacy using SACRO-ML.

.. note::
   This section covers SACRO-ML functionality. For ACRO-specific examples, see :doc:`statistical_modeling` and :doc:`basic_workflow`.

Overview
========

Differential privacy (DP) provides mathematical guarantees about privacy protection during machine learning model training.

Core Concepts
=============

Differential Privacy Definition
-------------------------------

A randomized algorithm satisfies (ε, δ)-differential privacy if for all datasets D and D' differing by one record, and all possible outputs S:

Pr[Algorithm(D) ∈ S] ≤ exp(ε) × Pr[Algorithm(D') ∈ S] + δ

Privacy Parameters
------------------

* **ε (epsilon)**: Privacy budget - smaller values provide stronger privacy
* **δ (delta)**: Failure probability - typically very small (e.g., 10^-5)
* **Sensitivity**: Maximum change in output from changing one input record

Training Techniques
===================

DP-SGD (Differentially Private Stochastic Gradient Descent)
-----------------------------------------------------------

The standard approach for training neural networks with differential privacy:

1. **Gradient Clipping**: Limit the influence of any single training example
2. **Noise Addition**: Add calibrated noise to gradients
3. **Privacy Accounting**: Track cumulative privacy loss across training steps

Private Aggregation
-------------------

Techniques for combining model updates while preserving privacy:

* **Secure aggregation protocols**
* **Federated learning with DP**
* **Private ensemble methods**

Utility-Privacy Trade-offs
==========================

Balancing Model Performance and Privacy
---------------------------------------

Key considerations when training with differential privacy:

* **Privacy Budget Allocation**: How to distribute ε across training steps
* **Hyperparameter Tuning**: Adapting learning rates and batch sizes
* **Architecture Choices**: Model designs that work well with DP
* **Evaluation Strategies**: Measuring both utility and privacy

Framework Integration
=====================

SACRO-ML provides DP training integration with popular frameworks:

PyTorch Integration
-------------------

* Opacus library integration
* Custom DP optimizers
* Privacy accounting tools
* Model validation utilities

TensorFlow Integration
----------------------

* TensorFlow Privacy integration
* DP-SGD implementations
* Privacy loss tracking
* Secure model checkpointing

Scikit-learn Integration
------------------------

* DP versions of common algorithms
* Private feature selection
* Cross-validation with privacy
* Model evaluation tools

Implementation Guidelines
=========================

Privacy Budget Management
-------------------------

Best practices for managing privacy budgets:

1. **Set Overall Budget**: Determine total ε for the project
2. **Allocate Across Tasks**: Distribute budget between training, validation, testing
3. **Track Consumption**: Monitor privacy expenditure during training
4. **Reserve Budget**: Keep some budget for model evaluation

Model Architecture Considerations
---------------------------------

Design choices that improve DP training:

* **Smaller Models**: Often work better with privacy constraints
* **Batch Normalization**: Can conflict with DP - consider alternatives
* **Activation Functions**: Some work better with gradient clipping
* **Regularization**: Important for preventing overfitting with noise

Hyperparameter Tuning
----------------------

Adapting standard ML practices for DP:

* **Learning Rate**: Often needs to be higher to overcome noise
* **Batch Size**: Larger batches can improve privacy-utility trade-off
* **Clipping Norm**: Critical parameter for gradient clipping
* **Noise Multiplier**: Controls the amount of noise added

Installation and Usage
======================

.. code-block:: bash

   pip install sacro-ml

For detailed implementation examples, tutorials, and API documentation, see the :doc:`../sacro_ml` documentation.

Evaluation and Validation
=========================

Measuring Privacy and Utility
------------------------------

Tools and techniques for evaluating DP-trained models:

* **Privacy auditing**: Empirical privacy loss measurement
* **Membership inference attacks**: Testing privacy in practice
* **Utility metrics**: Standard ML evaluation adapted for DP
* **Privacy-utility curves**: Visualizing trade-offs

See Also
========

* :doc:`../sacro_ml` - Complete SACRO-ML documentation
* :doc:`ml_privacy_assessment` - Privacy risk assessment tools
* :doc:`safe_model_export` - Safe model sharing procedures