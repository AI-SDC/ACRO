==========
User Guide
==========

Complete guide to using ACRO for statistical disclosure control.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/getting_started
   user_guide/core_concepts
   user_guide/configuration

Overview
========

This user guide provides comprehensive documentation for using ACRO effectively in your research workflows.

Quick Navigation
================

* **New Users**: Start with the :doc:`examples` section
* **Advanced Features**: Explore custom disclosure checking
* **Integration**: Check integration workflows in :doc:`examples`

Key Topics
==========

Data Analysis
-------------

* **Cross-tabulations** - Safe table creation with disclosure control
* **Statistical modeling** - Regression analysis with privacy protection
* **Summary statistics** - Descriptive statistics with safety checks
* **Data visualization** - Safe plotting and chart generation

Configuration
-------------

* **Safety parameters** - Customizing disclosure thresholds
* **Custom checks** - Advanced safety rule configuration

Integration
-----------

* **Python workflows** - Jupyter notebook integration
* **R integration** - Using ACRO-R package
* **Stata workflows** - Statistical software integration

Best Practices
==============

1. **Always use suppress=True** in production environments
2. **Review disclosure checks** before finalizing outputs
3. **Use meaningful output names** for better tracking
4. **Document your analysis workflow** for reproducibility
5. **Test with sample data** before running on sensitive data

Troubleshooting
===============

Common issues and solutions:

* **Import errors**: Check Python environment and ACRO installation
* **Configuration issues**: Verify YAML syntax and parameter values
* **Disclosure warnings**: Review safety thresholds and data characteristics
* **Output problems**: Check file permissions and directory structure

Getting Help
============

* :doc:`api` - Complete API reference
* `GitHub Issues <https://github.com/AI-SDC/ACRO/issues>`_ - Report bugs
* `Discussions <https://github.com/AI-SDC/ACRO/discussions>`_ - Community support
