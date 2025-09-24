=============
R Workflows  
=============

Examples of using ACRO-R for statistical analysis.

Basic R Workflow
================

.. code-block:: r

   library(acro)
   
   # Initialize ACRO
   acro_init(suppress = TRUE)
   
   # Load data
   data <- read.csv("research_data.csv")
   
   # Safe cross-tabulation
   result <- acro_crosstab(data$category, data$region)
   
   # Finalize outputs
   acro_finalise("outputs/")

See Also
========

* :doc:`../acro_r` - Complete ACRO-R documentation
* `ACRO-R GitHub Repository <https://github.com/AI-SDC/ACRO-R>`_