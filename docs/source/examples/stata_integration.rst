==================
Stata Integration
==================

Using ACRO with Stata through Python integration.

Setup
=====

.. code-block:: stata

   * Install Python integration (Stata 16+)
   ssc install python
   
   * Set Python executable
   set python_exec "path/to/your/python"

Basic Usage
===========

.. code-block:: stata

   * Initialize ACRO in Python
   python:
   import acro
   session = acro.ACRO(suppress=True)
   end
   
   * Your Stata analysis here
   * Then use Python to check outputs
   
   python:
   # Add Stata outputs to ACRO
   session.finalise("outputs/")
   end

Coming Soon
===========

More comprehensive Stata integration examples.