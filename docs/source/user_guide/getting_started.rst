===============
Getting Started
===============

This guide helps you get up and running with ACRO for statistical disclosure control.

What is ACRO?
=============

ACRO (Automatic Checking of Research Outputs) is a Python package that provides statistical
disclosure control for research outputs. It wraps common analysis functions, automatically
checking for potential privacy disclosures before outputs leave a secure data environment.

From v0.4.12, ACRO's checking logic is driven by a formal ontology  see
`How ACRO's Ontology-Driven Architecture Works`_ below for an explanation of what that means in practice.

Key Concepts
============

Statistical Disclosure Control (SDC)
-------------------------------------

SDC is the process of protecting confidential information in statistical data releases.
ACRO implements *principles-based* SDC that:

* Identifies potentially disclosive outputs
* Applies mitigation strategies when needed (suppression or rounding)
* Maintains detailed, auditable records of every decision
* Supports human checker workflows rather than blocking researchers

Disclosure Types
-----------------

ACRO checks for several types of disclosure:

* **Identity disclosure**  When individuals can be identified from a table cell
* **Attribute disclosure**  When sensitive attributes can be inferred about identified individuals
* **Inferential disclosure**  When statistical inference reveals information (e.g. dominance)
* **Linked-table disclosure**  When releasing two tables together reveals more than either alone

Safety Thresholds
------------------

ACRO uses configurable thresholds to determine whether an output is safe:

* **Minimum cell count**  Default: 10 observations per cell
* **P-ratio threshold**  Default: 0.1 for dominance
* **NK-rule**  Default: n=2, k=90% for concentration
* **Degrees of freedom**  Default: ≥10 for regression models

These thresholds are set by the TRE administrator in a YAML configuration file and are
loaded when your ACRO session starts. See :doc:`configuration` for details.

Basic Workflow
==============

A typical ACRO session follows four steps:

.. code-block:: python

   import acro
   import pandas as pd

   # Step 1: Initialise an ACRO session
   # suppress=True means unsafe cells are removed automatically.
   # Use suppress=False to see warnings without removing cells.
   session = acro.ACRO(suppress=True)

   # Step 2: Load your data and run analysis as normal
   df = pd.read_csv("my_data.csv")
   result = session.crosstab(df.region, df.income)

   # Step 3: Review the output and add any exceptions if needed
   session.print_outputs()
   session.add_exception("output_0", "I need this output because...")

   # Step 4: Finalise  writes an audit report for the output checker
   session.finalise("safe_outputs")

The ``suppress=True`` option tells ACRO to apply suppression automatically.
If you prefer to see all results and decide yourself, use ``suppress=False``.

Mitigation Strategies
=====================

ACRO supports two mitigation strategies:

Suppression
-----------

Unsafe cells are replaced with ``NaN``. When margins are requested, they are
recomputed *after* suppression so they do not leak the suppressed values.

.. code-block:: python

   session = acro.ACRO(suppress=True)

Rounding
--------

All cell values are rounded to the nearest multiple of a configurable *base*
(default: 5). Marginal totals are recomputed from the rounded inner cells.

.. code-block:: python

   session = acro.ACRO()
   session.enable_rounding(base=5)

.. _ontology-architecture:

How ACRO's Ontology-Driven Architecture Works
=============================================

Before v0.4.12, the list of checks applied to each analysis was hard-coded.
This made it difficult to:

* Add support for new analysis types without touching multiple files.
* Produce auditable statements of *which* checks ran and *why*.
* Keep the code aligned with evolving SDC best practice.

The new architecture solves this by reading the check rules from a formal
`StatbarnsSDC ontology <https://w3id.org/statbarnsdc>`_ at build time.

The Four Lookup Tables
-----------------------

When ACRO is built, ``ontology_handler.py`` reads the ontology and produces
four JSON files that are bundled with every release:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - File
     - Contents
   * - ``analyses.json``
     - Maps analysis names (e.g. ``"Mean"``, ``"GeneralLinearModel"``) to
       their *statbarn*  the SDC category they belong to.
   * - ``statbarns.json``
     - Maps each statbarn to the risks associated with it.
   * - ``risks.json``
     - Maps each risk to the checks that detect it and the
       mitigations that address it.
   * - ``checks.json``
     - Maps each check to the evidence it requires (e.g. a count
       table, residual degrees of freedom).

Because these files are bundled with the package, ACRO works entirely
offline inside a TRE  no internet access is required.

What Happens at Runtime
------------------------

1. **Session start**  ``ACRO()`` creates an ``SDCChecks`` instance which
   loads the four JSON files and the TRE's risk appetite from the YAML
   config.

2. **Analysis call**  When you call, say, ``session.crosstab(...)``, ACRO:

   a. Creates a ``TableModelDetails`` object holding all the parameters
      needed to reproduce the table.
   b. Looks up the appropriate analysis name (``"FrequencyTable"``,
      ``"Mean"``, etc.) in ``analyses.json`` to find its statbarn.
   c. Follows the chain: statbarn → risks → checks → evidence to determine
      exactly what data needs to be collected.
   d. Collects all required evidence into an ``SDCEvidence`` object.

3. **Check and output**  Each required check runs on the collected
   evidence and returns a status (``pass``, ``review``, or ``fail``) plus
   a plain-English summary.  The results are combined and the chosen
   mitigation is applied.

This means adding support for a completely new analysis type requires only
adding entries to the ontology (and regenerating the JSON files)  no
Python code changes are needed.

Federated Mode
==============

ACRO also supports a *federated* mode for use with a trusted aggregator:

.. code-block:: python

   session = acro.ACRO(federated=True)

In federated mode the **evidence collection** (step 2 above) still runs
locally inside the TRE, but the checks (step 3) are performed by a
remote trusted aggregator rather than locally. The evidence is packaged
and serialised by ``records.finalise_evidence()``, which writes each
interim table to a CSV file and produces an ``evidence.json`` manifest.

This separation makes it possible to run SDC checks on *aggregated*
evidence from multiple TREs without sharing individual-level data.

Installation Requirements
=========================

* Python 3.10 or higher
* pandas, statsmodels, PyYAML (installed automatically with ``pip install acro``)

Next Steps
==========

* See :doc:`core_concepts` for the detailed SDC methodology
* Check :doc:`configuration` for customisation options
* Visit :doc:`../examples` for hands-on tutorials
