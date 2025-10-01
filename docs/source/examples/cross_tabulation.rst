================
Cross-tabulation
================

Complete example of creating safe cross-tabulations with ACRO.

This example demonstrates how to create cross-tabulations with automatic disclosure control, including basic tables, tables with margins, and multi-dimensional analysis.

Basic Cross-tabulation
======================

.. code-block:: python

   import acro
   import pandas as pd
   import numpy as np
   
   # Create sample data
   np.random.seed(42)
   data = pd.DataFrame({
       'category': np.random.choice(['A', 'B', 'C'], 1000),
       'region': np.random.choice(['North', 'South', 'East', 'West'], 1000),
       'value': np.random.normal(100, 15, 1000)
   })
   
   # Initialize ACRO
   session = acro.ACRO(suppress=True)
   
   # Simple cross-tabulation
   result = session.crosstab(data['category'], data['region'])
   print(result)

Cross-tabulation with Margins
==============================

.. code-block:: python

   # Cross-tabulation with row and column totals
   result_with_margins = session.crosstab(
       data['category'], 
       data['region'],
       margins=True,
       margins_name='Total'
   )
   print(result_with_margins)

Aggregated Cross-tabulation
============================

.. code-block:: python

   # Cross-tabulation with mean values
   result_mean = session.crosstab(
       data['category'], 
       data['region'],
       values=data['value'],
       aggfunc='mean'
   )
   print(result_mean)

Multi-dimensional Cross-tabulation
===================================

.. code-block:: python

   # Add another categorical variable
   data['size'] = np.random.choice(['Small', 'Large'], 1000)
   
   # Three-way cross-tabulation
   result_3way = session.crosstab(
       [data['category'], data['size']], 
       data['region']
   )
   print(result_3way)

Handling Suppressed Values
==========================

.. code-block:: python

   # Show suppressed values for review
   result_suppressed = session.crosstab(
       data['category'], 
       data['region'],
       show_suppressed=True
   )
   print(result_suppressed)

Complete Example with Output Management
=======================================

.. code-block:: python

   import acro
   import pandas as pd
   import numpy as np
   
   # Create sample data
   np.random.seed(42)
   data = pd.DataFrame({
       'category': np.random.choice(['A', 'B', 'C'], 1000),
       'region': np.random.choice(['North', 'South', 'East', 'West'], 1000),
       'value': np.random.normal(100, 15, 1000)
   })
   
   # Initialize ACRO with suppression
   session = acro.ACRO(suppress=True)
   
   # Create multiple cross-tabulations
   basic_table = session.crosstab(data['category'], data['region'])
   
   margin_table = session.crosstab(
       data['category'], 
       data['region'],
       margins=True
   )
   
   mean_table = session.crosstab(
       data['category'], 
       data['region'],
       values=data['value'],
       aggfunc='mean'
   )
   
   # Add comments to outputs
   session.add_comments("output_0", "Basic frequency cross-tabulation")
   session.add_comments("output_1", "Cross-tabulation with margins")
   session.add_comments("output_2", "Cross-tabulation of mean values")
   
   # Review outputs
   print(session.print_outputs())
   
   # Finalize for review
   session.finalise("crosstab_outputs")

Expected Output
===============

The cross-tabulations will show frequency counts (or aggregated values) for each combination of categories and regions. ACRO automatically:

* Suppresses cells with counts below the safety threshold
* Applies disclosure control rules (p-ratio, nk-dominance)
* Provides detailed information about why cells were suppressed
* Tracks all outputs for review by data controllers

Key Parameters
==============

* ``index``: Row grouping variable(s)
* ``columns``: Column grouping variable(s) 
* ``values``: Values to aggregate (optional)
* ``aggfunc``: Aggregation function ('count', 'sum', 'mean', etc.)
* ``margins``: Include row/column totals
* ``show_suppressed``: Display suppressed values for review

See Also
========

* :doc:`statistical_modeling` - Regression analysis examples
* :doc:`basic_workflow` - Complete analysis workflow
* :doc:`../api` - Complete API reference