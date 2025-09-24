==================
Data Visualization
==================

Complete examples of creating safe visualizations with ACRO.

This example demonstrates how to create various types of plots while maintaining disclosure control, including histograms, survival plots, and custom visualizations.

Safe Histogram Example
======================

.. code-block:: python

   import acro
   import pandas as pd
   import numpy as np
   import matplotlib.pyplot as plt
   
   # Create sample data
   np.random.seed(42)
   data = pd.DataFrame({
       'values': np.random.normal(100, 15, 1000),
       'category': np.random.choice(['A', 'B', 'C'], 1000)
   })
   
   # Initialize ACRO
   session = acro.ACRO(suppress=True)
   
   # Create safe histogram
   histogram_file = session.hist(data, 'values', bins=20, filename='value_distribution.png')
   print(f"Histogram saved as: {histogram_file}")

Survival Analysis Visualization
===============================

.. code-block:: python

   # Create survival data
   np.random.seed(42)
   n = 500
   survival_data = pd.DataFrame({
       'time': np.random.exponential(10, n),
       'status': np.random.choice([0, 1], n, p=[0.3, 0.7])
   })
   
   # Create survival plot
   survival_plot, filename = session.surv_func(
       survival_data['time'], 
       survival_data['status'], 
       output='plot',
       filename='survival_curve.png'
   )
   print(f"Survival plot saved as: {filename}")

Survival Table Example
======================

.. code-block:: python

   # Create survival table instead of plot
   survival_table = session.surv_func(
       survival_data['time'], 
       survival_data['status'], 
       output='table'
   )
   print(survival_table)

Custom Visualization Workflow
=============================

.. code-block:: python

   # Create aggregated data first using ACRO
   crosstab_data = session.crosstab(data['category'], 
                                   pd.cut(data['values'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High']))
   
   # Create custom plot from safe aggregated data
   plt.figure(figsize=(10, 6))
   crosstab_data.plot(kind='bar', stacked=True)
   plt.title('Distribution of Values by Category (Safe Aggregated Data)')
   plt.xlabel('Category')
   plt.ylabel('Count')
   plt.legend(title='Value Range')
   plt.tight_layout()
   
   # Save the plot
   plt.savefig('custom_bar_chart.png', dpi=300, bbox_inches='tight')
   plt.close()
   
   # Register with ACRO
   session.custom_output('custom_bar_chart.png', 'Custom bar chart from safe cross-tabulation')

Multiple Visualization Example
==============================

.. code-block:: python

   import acro
   import pandas as pd
   import numpy as np
   import matplotlib.pyplot as plt
   import seaborn as sns
   
   # Create comprehensive dataset
   np.random.seed(42)
   n = 1200
   
   data = pd.DataFrame({
       'age': np.random.normal(45, 15, n),
       'income': np.random.lognormal(10, 0.5, n),
       'region': np.random.choice(['North', 'South', 'East', 'West'], n),
       'education': np.random.choice(['High School', 'Bachelor', 'Graduate'], n)
   })
   
   # Initialize ACRO
   session = acro.ACRO(suppress=True)
   
   # 1. Safe histogram of age distribution
   age_hist = session.hist(data, 'age', bins=15, filename='age_distribution.png')
   
   # 2. Safe histogram of income distribution
   income_hist = session.hist(data, 'income', bins=20, filename='income_distribution.png')
   
   # 3. Create safe cross-tabulation for custom plot
   education_region = session.crosstab(data['education'], data['region'])
   
   # 4. Custom heatmap from safe data
   plt.figure(figsize=(8, 6))
   sns.heatmap(education_region, annot=True, fmt='d', cmap='Blues')
   plt.title('Education Level by Region (Safe Counts)')
   plt.tight_layout()
   plt.savefig('education_region_heatmap.png', dpi=300, bbox_inches='tight')
   plt.close()
   
   # Register custom plot
   session.custom_output('education_region_heatmap.png', 'Heatmap of education by region')
   
   # 5. Create safe pivot table for another custom plot
   age_groups = pd.cut(data['age'], bins=[0, 30, 50, 70, 100], labels=['Young', 'Middle', 'Senior', 'Elder'])
   income_groups = pd.cut(data['income'], bins=4, labels=['Low', 'Medium', 'High', 'Very High'])
   
   age_income_table = session.crosstab(age_groups, income_groups)
   
   # 6. Custom stacked bar chart
   plt.figure(figsize=(10, 6))
   age_income_table.plot(kind='bar', stacked=True, colormap='viridis')
   plt.title('Age Groups by Income Level (Safe Aggregated Data)')
   plt.xlabel('Age Group')
   plt.ylabel('Count')
   plt.legend(title='Income Level', bbox_to_anchor=(1.05, 1), loc='upper left')
   plt.tight_layout()
   plt.savefig('age_income_stacked.png', dpi=300, bbox_inches='tight')
   plt.close()
   
   # Register custom plot
   session.custom_output('age_income_stacked.png', 'Stacked bar chart of age groups by income')
   
   # Add comments to all outputs
   session.add_comments("output_0", "Age distribution histogram - shows overall age demographics")
   session.add_comments("output_1", "Income distribution histogram - shows income spread")
   session.add_comments("output_2", "Cross-tabulation of education by region")
   session.add_comments("output_3", "Custom heatmap visualization")
   session.add_comments("output_4", "Cross-tabulation of age groups by income level")
   session.add_comments("output_5", "Custom stacked bar chart")
   
   # Review all outputs
   print(session.print_outputs())
   
   # Finalize for review
   session.finalise("visualization_outputs")

Best Practices for Safe Visualization
=====================================

1. **Use ACRO's Built-in Methods**
   
   * ``hist()`` for histograms with automatic disclosure control
   * ``surv_func()`` for survival analysis plots

2. **Safe Custom Visualization Workflow**
   
   * Create aggregated data using ``crosstab()`` or ``pivot_table()``
   * Generate plots from the safe aggregated data only
   * Never plot raw individual-level data directly
   * Save plots to files and register with ``custom_output()``

3. **Output Management**
   
   * Use descriptive filenames for plots
   * Add meaningful comments explaining each visualization
   * Organize outputs logically for reviewers

Visualization Types Supported
=============================

**Built-in ACRO Visualizations**:
* Histograms with automatic bin safety checking
* Survival curves with disclosure control

**Custom Visualizations** (using safe aggregated data):
* Bar charts and stacked bar charts
* Heatmaps and correlation matrices
* Line plots and time series
* Scatter plots of aggregated data
* Box plots of group statistics

Troubleshooting
===============

**Histogram Suppressed**: Reduce number of bins or check for small subgroups

**Custom Plot Issues**: Ensure you're using aggregated data from ACRO methods

**File Not Found**: Check that plot files are saved before registering with ``custom_output()``

See Also
========

* :doc:`cross_tabulation` - Data aggregation for safe plotting
* :doc:`basic_workflow` - Complete analysis workflow
* :doc:`../api` - Complete API reference