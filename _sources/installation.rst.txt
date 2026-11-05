============
Installation
============

ACRO can be installed through multiple package managers and methods.

Requirements
============

* **Python**: 3.10 or higher
* **Operating System**: Windows, macOS, or Linux

Quick Installation
==================

PyPI Installation (Recommended)
--------------------------------

You may need admin privileges to install this way.

.. code-block:: bash

   pip install acro

Conda Installation
------------------

You may need admin privileges to install this way.

.. code-block:: bash

   conda install -c conda-forge acro

Installing within a Virtual Environment
========================================

This isolates ACRO from changes in the rest of your system, and may be necessary if you don't have admin privileges on your machine.

.. code-block:: bash

   # Create virtual environment (creates 'acro-env' folder in current directory)
   python -m venv acro-env

   # Activate (Windows)
   acro-env\Scripts\activate

   # Activate (Linux/macOS)
   source acro-env/bin/activate

   # Install ACRO
   pip install acro

Verification
============

.. code-block:: python

   import acro
   from acro.version import __version__
   print(f"ACRO version: {__version__}")

   # Test basic functionality
   session = acro.ACRO()
   print("ACRO initialized successfully!")

Next Steps
==========

* :doc:`introduction` - Welcome to ACRO
* :doc:`examples` - Usage examples and tutorials
* :doc:`api` - Complete API reference
