=============
Core Concepts
=============

Understanding the fundamental concepts behind ACRO's statistical disclosure control methodology.

Principles-Based SDC
====================

ACRO implements a *principles-based* approach to statistical disclosure control rather than a
purely rules-based one.  The key distinction is that every check applied to an output is
justified by a traceable chain from *analysis type* → *statistical risk* → *check* → *evidence*.
This chain is defined in the `StatbarnsSDC ontology <https://w3id.org/statbarnsdc>`_ and is
available within every ACRO installation as a set of JSON lookup tables.

Risk Assessment
---------------

* **Ontology-driven detection**  the checks to run for any analysis are looked up from
  ``analyses.json``, ``statbarns.json``, ``risks.json`` and ``checks.json`` rather than
  being hard-coded.
* **Context-aware** evaluation  ``TableModelDetails`` stores the full table specification
  so that checks can reproduce any intermediate table they need (e.g. a count-per-cell table).
* **Proportionate response**  outputs receive ``pass``, ``review``, or ``fail`` status with
  a plain-English explanation of every check that contributed.

Human-in-the-Loop
-----------------

* **Researcher guidance** rather than blanket blocking  you see *why* an output is flagged.
* **Transparent reasoning**  the audit record lists each check, its status, and a summary.
* **Exception mechanism**  researchers can add a justification for any flagged output using
  ``session.add_exception(output_id, "reason")``.

Audit and Accountability
------------------------

* **Complete audit trail**  every output records the analysis command, the checks that ran,
  each check's status, and any mitigation applied.
* **Reproducible**  the ``TableModelDetails`` object holds all parameters needed to rerun the
  table, supporting later verification.
* **FAIR reporting**  the structured check results are suitable for producing FAIR statements
  about which SDC processes were applied and why.

The New Ontology-Driven Architecture (v0.4.12+)
================================================

ACRO's most significant change in v0.4.12 is moving from hard-coded checking logic to an
ontology-driven approach.  This section explains the key classes and how they fit together.

SDCChecks
---------

``SDCChecks`` is the central rule engine.  It is created once per ACRO session and holds:

* The TRE's **risk appetite** (thresholds read from the YAML config file).
* The **knowledge base** loaded from the four JSON files.
* A **mapping** from each check name to the Python method that implements it.

You do not interact with ``SDCChecks`` directly  it is created automatically when you call
``acro.ACRO()``.

TableModelDetails
-----------------

Every table-type analysis (``crosstab``, ``pivot_table``, ``hist``, ``pie``, ``surv_func``)
creates a ``TableModelDetails`` instance.  This object acts as a *portable description* of
the requested table.  It stores:

* The **index**, **column**, and **values** series.
* The **aggregation function(s)** requested.
* The **model type** (``"table"``, ``"array"``, or ``"survival"``).
* The **risk appetite** and any keyword arguments needed to recreate the table.
* **Variable metadata**  including the ``CategoricalDtype`` of each dimension, so that
  categories are preserved even after disclosive records are removed.

The object also provides helper methods used during evidence collection:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Method
     - Purpose
   * - ``get_count_table()``
     - Returns a table with the *number of records* per cell.
   * - ``get_allfalse_table()``
     - Returns a boolean mask with all cells set to ``False``.
   * - ``get_zeros_table()``
     - Returns a table of zeros, matching the table's structure.
   * - ``get_newagg_table(aggfunc)``
     - Reruns the table with a different aggregation function (used to
       compute dominance statistics without storing the full data twice).

SDCEvidence
-----------

``SDCEvidence`` is a lightweight data container that accumulates everything needed to run
the checks for a given analysis.  It is populated by
``SDCChecks.get_evidence_forall_analyses()`` and may contain:

* ``dof``  residual degrees of freedom (for regression models) or a per-cell count minus 1
  (for table models).
* ``interim_tables``  a dictionary of DataFrames, one per piece of evidence required.
  Common keys include ``"count_table"``, ``"sum"``, ``"max"``, ``"top_n_sum"``, etc.
* ``variable_type_dict``  the names of dependent and independent variables, used to
  assist secondary disclosure control review.

ChecksResults and ManyChecksResults
-------------------------------------

``ChecksResults`` is returned by ``SDCChecks.run_checks_for_analysis()``.  It bundles:

* ``overall_status``  ``"pass"``, ``"review"``, or ``"fail"``.
* ``summaries``  a string concatenating the plain-English summary of every check.
* ``outcomes``  a dictionary mapping check names to their result (a mask DataFrame or a
  scalar).
* ``fair_dict``  structured SDC process metadata suitable for FAIR reporting.

``ManyChecksResults`` wraps multiple ``ChecksResults`` instances when a table uses more than
one aggregation function (e.g. ``aggfunc=["mean", "std"]``).

Disclosure Control Methods
==========================

Suppression
-----------

When a cell fails a check, ACRO identifies the records that fall into that cell and
**removes them from the data** before rerunning the table via pandas.  This means marginal
totals (row/column "All" sums) are always recomputed correctly  they reflect the suppressed
data rather than leaking the removed values.

.. code-block:: python

   session = acro.ACRO(suppress=True)
   table = session.crosstab(df.region, df.income)  # unsafe cells replaced with NaN
   table_with_margins = session.crosstab(
       df.region, df.income, margins=True, show_suppressed=True
   )

Rounding
--------

All cell values are rounded to the nearest multiple of a configurable ``base`` (default 5).
Marginal totals are derived from the *rounded* inner cells so they are consistent with what
is displayed.

.. code-block:: python

   session = acro.ACRO()
   session.enable_rounding(base=5)    # round to nearest 5
   session.enable_rounding(base=10)   # round to nearest 10

Rounding and suppression are mutually exclusive  calling ``enable_rounding()`` disables
suppression and vice versa.

Federated Mode
==============

In a *federated* deployment several TREs share evidence with a trusted aggregator:

.. code-block:: python

   # Inside the TRE
   session = acro.ACRO(federated=True)
   result = session.crosstab(df.region, df.income)

   # Evidence is stored locally  no checks run yet
   session.finalise("evidence_outputs")  # writes evidence.json + CSV files

In federated mode:

* Evidence collection runs inside the TRE.
* The ``finalise()`` method serialises the evidence by calling ``Records.finalise_evidence()``,
  which writes each interim table to a separate CSV file and produces an ``evidence.json``
  manifest describing all outputs.
* The trusted aggregator receives the evidence files and runs the checks centrally.

How Categories Are Preserved
=============================

A subtle but important improvement in v0.4.12 is that ACRO now stores the ``CategoricalDtype``
of every dimension in the ``TableModelDetails`` object.  When records are redacted to apply
suppression, pandas would ordinarily drop any categories that no longer appear in the data.
ACRO prevents this by re-casting each dimension column to its original ``CategoricalDtype``
after redaction, ensuring that the rerun table has the same structure as the original.

This means a cross-tabulation of ``year × grant_type`` will always produce the same set of
rows and columns, even after suppression removes some records.

The Process at a Glance
=======================

The diagram below summarises the full pipeline, from session start to output record.

::

   ┌─────────────────────────────────────────────────────┐
   │  Session Initialisation                             │
   │  ACRO() → SDCChecks() ← analyses/risks/checks JSON │
   └───────────────────────┬─────────────────────────────┘
                           │
                           ▼
   ┌─────────────────────────────────────────────────────┐
   │  Analysis Call  (e.g. crosstab, ols)                │
   │  1. Build TableModelDetails / model object          │
   │  2. Look up: analysis → statbarn → risks → checks   │
   │  3. Collect evidence into SDCEvidence               │
   └───────────────────────┬─────────────────────────────┘
                           │
                           ▼
   ┌─────────────────────────────────────────────────────┐
   │  Standalone Mode          │  Federated Mode         │
   │  Run checks on evidence   │  Serialise evidence     │
   │  Apply mitigation         │  Send to aggregator     │
   │  Record output + audit    │  Record output locally  │
   └───────────────────────────┴─────────────────────────┘

Best Practices
==============

Configuration Management
------------------------

* Use version-controlled YAML configuration files.
* Document all threshold customisations and their rationale.
* Test configurations with sample data before deploying in production.

Workflow Design
---------------

* Plan your analysis before starting an ACRO session.
* Use meaningful output names with ``session.rename_output()`` for easier review.
* Add comments and exceptions promptly  they are included in the finalised report.

Quality Control
---------------

* Review all ``review`` and ``fail`` outputs before calling ``finalise()``.
* Validate results against expected patterns from a test dataset.
* Keep the audit records alongside your analysis scripts.
