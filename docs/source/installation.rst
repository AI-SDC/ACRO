============
Installation
============

ACRO can be installed through multiple package managers and methods.

.. note::
   **Permissions:** You may need administrative rights to perform the installation on your system, depending on your operating system and whether you are working within an organization.

Requirements
============

* **Python**: 3.9 or higher
* **Operating System**: Windows, macOS, or Linux

Quick Installation
==================

PyPI Installation (Recommended)
--------------------------------

.. code-block:: bash

   pip install acro

Conda Installation
------------------

.. code-block:: bash

   conda install -c conda-forge acro

Virtual Environment Setup
==========================

.. code-block:: bash

   # Create virtual environment
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

* :doc:`introduction` - Getting started guide
* :doc:`examples` - Usage examples and tutorials
* :doc:`api` - Complete API reference
