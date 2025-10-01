=======
ACRO-R
=======

ACRO-R is the R package implementation of the ACRO framework, providing statistical disclosure control for R users and workflows.

Overview
========

ACRO-R brings the power of SACRO methodology to R environments, offering:

* Native R integration with familiar syntax
* Seamless integration with tidyverse workflows
* Support for R statistical modeling functions
* RStudio integration and interactive features

Key Features
============

R-Native Functions
------------------

* ``acro_crosstab()`` - Cross-tabulation with disclosure checking
* ``acro_lm()`` - Linear modeling with privacy protection
* ``acro_glm()`` - Generalized linear models
* ``acro_summary()`` - Safe summary statistics

Tidyverse Integration
---------------------

* Works with dplyr pipelines
* ggplot2 safe plotting functions
* Integration with R Markdown workflows

RStudio Support
---------------

* Interactive output checking
* Integrated help and documentation
* Visual disclosure risk indicators

Installation
============

From CRAN
----------

.. code-block:: r

   install.packages("acro")

From GitHub (Development)
-------------------------

.. code-block:: r

   # Install devtools if needed
   install.packages("devtools")
   
   # Install ACRO-R
   devtools::install_github("AI-SDC/ACRO-R")

Quick Start
===========

.. code-block:: r

   library(acro)
   
   # Initialize ACRO session
   acro_init()
   
   # Load your data
   data <- read.csv("your_data.csv")
   
   # Create safe cross-tabulation
   safe_table <- acro_crosstab(data$category, data$region)
   
   # Run safe linear model
   safe_model <- acro_lm(outcome ~ predictor1 + predictor2, data = data)
   
   # Finalize outputs for review
   acro_finalise(output_folder = "outputs")

Core Functions
==============

Data Analysis
-------------

.. code-block:: r

   # Cross-tabulation
   acro_crosstab(x, y, show_suppressed = TRUE)
   
   # Pivot tables
   acro_pivot_table(data, values, index, columns)
   
   # Summary statistics
   acro_summary(data, by_group = NULL)

Statistical Modeling
--------------------

.. code-block:: r

   # Linear regression
   acro_lm(formula, data, weights = NULL)
   
   # Generalized linear models
   acro_glm(formula, family, data)
   
   # Survival analysis
   acro_survfit(formula, data)

Output Management
-----------------

.. code-block:: r

   # Initialize session
   acro_init(suppress = TRUE, config = NULL)
   
   # Check current outputs
   acro_print_outputs()
   
   # Finalize for review
   acro_finalise(output_folder = "outputs")

Configuration
=============

Custom Configuration
--------------------

.. code-block:: r

   # Set custom thresholds
   config <- list(
     safe_threshold = 10,
     safe_dof_threshold = 10,
     safe_nk_n = 2,
     safe_nk_k = 0.9,
     safe_p_threshold = 0.1
   )
   
   acro_init(config = config)

Environment Variables
---------------------

.. code-block:: r

   # Set via R options
   options(acro.suppress = TRUE)
   options(acro.safe_threshold = 5)

Examples
========

Basic Workflow
--------------

.. code-block:: r

   library(acro)
   library(dplyr)
   
   # Initialize
   acro_init(suppress = TRUE)
   
   # Load and explore data safely
   data <- mtcars
   safe_summary <- acro_summary(data)
   
   # Create safe visualizations
   safe_plot <- acro_plot(data, aes(x = mpg, y = hp)) +
     geom_point() +
     geom_smooth(method = "lm")
   
   # Statistical analysis
   model <- acro_lm(mpg ~ hp + wt + cyl, data = data)
   
   # Finalize
   acro_finalise("outputs/")

Advanced Analysis
-----------------

.. code-block:: r

   # Complex cross-tabulation
   complex_table <- data %>%
     group_by(region, category) %>%
     acro_summarise(
       count = n(),
       mean_value = mean(value),
       .groups = "drop"
     )
   
   # Multiple models comparison
   models <- list(
     model1 = acro_lm(y ~ x1, data = data),
     model2 = acro_lm(y ~ x1 + x2, data = data),
     model3 = acro_glm(y ~ x1 + x2, family = binomial, data = data)
   )

Integration with R Markdown
===========================

.. code-block:: r

   ---
   title: "Safe Analysis Report"
   output: html_document
   ---
   
   ```{r setup}
   library(acro)
   acro_init(suppress = TRUE)
   ```
   
   ```{r analysis}
   # Your analysis code here
   safe_results <- acro_crosstab(data$var1, data$var2)
   ```
   
   ```{r finalize}
   acro_finalise("outputs/")
   ```

API Reference
=============

Core Functions
--------------

* ``acro_init()`` - Initialize ACRO session
* ``acro_crosstab()`` - Safe cross-tabulation
* ``acro_lm()`` - Safe linear modeling
* ``acro_glm()`` - Safe generalized linear modeling
* ``acro_summary()`` - Safe summary statistics
* ``acro_finalise()`` - Prepare outputs for review

Utility Functions
-----------------

* ``acro_print_outputs()`` - Display current outputs
* ``acro_remove_output()`` - Remove specific output
* ``acro_config()`` - Get/set configuration options

Troubleshooting
===============

Common Issues
-------------

**Issue**: Package not loading
**Solution**: Check R version compatibility (R >= 4.0 required)

**Issue**: Python backend not found
**Solution**: Ensure Python ACRO package is installed

.. code-block:: r

   # Check Python setup
   reticulate::py_config()
   
   # Install Python ACRO if needed
   reticulate::py_install("acro")

See Also
========

* :doc:`index` - Main ACRO documentation
* :doc:`sacro_ml` - Machine learning tools
* :doc:`sacro_viewer` - Output checking interface
* `ACRO-R GitHub Repository <https://github.com/AI-SDC/ACRO-R>`_