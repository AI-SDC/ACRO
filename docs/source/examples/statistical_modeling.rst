====================
Statistical Modeling
====================

Complete examples of safe statistical modeling with ACRO.

This example demonstrates various regression techniques with automatic disclosure control, including linear regression, logistic regression, and model comparison.

Linear Regression Example
=========================

.. code-block:: python

   import acro
   import pandas as pd
   import numpy as np
   
   # Create sample data
   np.random.seed(42)
   n = 1000
   data = pd.DataFrame({
       'x1': np.random.normal(0, 1, n),
       'x2': np.random.normal(0, 1, n),
       'category': np.random.choice(['A', 'B', 'C'], n)
   })
   
   # Create dependent variable
   data['y'] = 2 + 1.5 * data['x1'] + 0.8 * data['x2'] + np.random.normal(0, 0.5, n)
   
   # Initialize ACRO
   session = acro.ACRO(suppress=True)
   
   # Formula-based linear regression
   model = session.olsr('y ~ x1 + x2 + C(category)', data=data)
   print(model.summary())

Array-based Linear Regression
==============================

.. code-block:: python

   # Prepare data for array-based regression
   X = pd.get_dummies(data[['x1', 'x2', 'category']], drop_first=True)
   X = acro.add_constant(X)  # Add intercept
   y = data['y']
   
   # Array-based linear regression
   model_array = session.ols(y, X)
   print(model_array.summary())

Logistic Regression Example
============================

.. code-block:: python

   # Create binary outcome
   data['binary_y'] = (data['y'] > data['y'].median()).astype(int)
   
   # Formula-based logistic regression
   logit_model = session.logitr('binary_y ~ x1 + x2 + C(category)', data=data)
   print(logit_model.summary())

Probit Regression Example
=========================

.. code-block:: python

   # Formula-based probit regression
   probit_model = session.probitr('binary_y ~ x1 + x2', data=data)
   print(probit_model.summary())

Model Comparison Example
========================

.. code-block:: python

   # Compare multiple models
   model1 = session.olsr('y ~ x1', data=data)
   model2 = session.olsr('y ~ x1 + x2', data=data)
   model3 = session.olsr('y ~ x1 + x2 + C(category)', data=data)
   
   # Add descriptive comments
   session.add_comments("output_0", "Simple regression with x1 only")
   session.add_comments("output_1", "Multiple regression with x1 and x2")
   session.add_comments("output_2", "Full model with categorical variable")

Complete Modeling Workflow
==========================

.. code-block:: python

   import acro
   import pandas as pd
   import numpy as np
   
   # Generate realistic dataset
   np.random.seed(42)
   n = 1500
   
   data = pd.DataFrame({
       'age': np.random.normal(45, 15, n),
       'income': np.random.lognormal(10, 0.5, n),
       'education': np.random.choice(['High School', 'Bachelor', 'Graduate'], n),
       'region': np.random.choice(['North', 'South', 'East', 'West'], n)
   })
   
   # Create outcome variable
   data['satisfaction'] = (
       0.02 * data['age'] + 
       0.00001 * data['income'] + 
       np.where(data['education'] == 'Graduate', 2, 0) +
       np.random.normal(0, 1, n)
   )
   
   # Initialize ACRO
   session = acro.ACRO(suppress=True)
   
   # Exploratory analysis with cross-tabulation
   education_region = session.crosstab(data['education'], data['region'])
   
   # Linear regression analysis
   satisfaction_model = session.olsr(
       'satisfaction ~ age + income + C(education) + C(region)', 
       data=data
   )
   
   # Create binary outcome for logistic regression
   data['high_satisfaction'] = (data['satisfaction'] > data['satisfaction'].median()).astype(int)
   
   # Logistic regression
   logistic_model = session.logitr(
       'high_satisfaction ~ age + income + C(education)', 
       data=data
   )
   
   # Add detailed comments
   session.add_comments("output_0", "Cross-tabulation of education by region")
   session.add_comments("output_1", "Linear regression: satisfaction ~ demographics")
   session.add_comments("output_2", "Logistic regression: high satisfaction prediction")
   
   # Review all outputs
   print(session.print_outputs())
   
   # Finalize for review
   session.finalise("modeling_outputs")

Model Interpretation
====================

ACRO automatically checks regression models for:

**Degrees of Freedom**: Ensures sufficient observations relative to parameters

**Disclosure Risk**: Applies statistical disclosure control to model outputs

**Model Summary**: Provides standard regression output with disclosure control applied

Key Features
============

* **Formula Interface**: Use R-style formulas for easy model specification
* **Array Interface**: Direct numpy/pandas array input for advanced users
* **Automatic Checking**: Built-in degrees of freedom and disclosure control
* **Multiple Model Types**: Linear, logistic, probit regression support
* **Integration**: Works seamlessly with statsmodels

Troubleshooting
===============

**Low Degrees of Freedom Warning**: Increase sample size or reduce model complexity

**Convergence Issues**: Check for multicollinearity or scaling issues

**Disclosure Warnings**: Review model specification and data characteristics

See Also
========

* :doc:`cross_tabulation` - Data exploration examples
* :doc:`basic_workflow` - Complete analysis workflow
* :doc:`../api` - Complete API reference