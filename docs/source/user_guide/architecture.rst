==============================
Architecture Reference
==============================

This page gives a detailed technical overview of ACRO's ontology-driven architecture
introduced in v0.4.12.  It is aimed at developers, TRE administrators, and curious
researchers who want to understand how the disclosure checking process works internally.

.. contents::
   :local:
   :depth: 2

Background and Motivation
==========================

In earlier versions of ACRO, the checks applied to each type of analysis were hard-coded
in Python.  This created several problems:

* **Hard to extend**  adding a new analysis type required editing multiple files.
* **No FAIR audit trail**  there was no easy way to record *which* checks ran or *why*.
* **Drift from the knowledge base**  the code could silently diverge from the SDC
  knowledge encoded in the StatbarnsSDC ontology.
* **Bloated code**  ``acro_tables.py`` had grown to the point where it was hard to
  maintain.

The solution was to move the rules out of Python and into the
`StatbarnsSDC ontology <https://w3id.org/statbarnsdc>`_, then generate compact JSON
lookup tables from the ontology at release time.

The Four JSON Knowledge Files
==============================

The ontology is compiled into four JSON files by ``acro/ontology_handler.py``.  These
files are bundled with every ACRO release so the package works fully offline inside a TRE.

analyses.json
-------------

Maps each *analysis name* (the type of statistic being computed) to the *statbarn*
(the SDC category it belongs to) and any additional metadata.

Example entry::

   "Mean": {
       "statbarn": "DescriptiveStatistics",
       ...
   }

statbarns.json
--------------

Maps each *statbarn* to the list of *risks* associated with it.

Example entry::

   "DescriptiveStatistics": {
       "risks": ["https://w3id.org/statbarnsdc#SmallGroupRisk",
                 "https://w3id.org/statbarnsdc#DominanceRisk"],
       ...
   }

risks.json
----------

Maps each *risk* to the *checks* that detect it and the *mitigations* that address it.

Example entry::

   "SmallGroupRisk": {
       "checks": ["MinimumThresholdCheck"],
       "mitigations": ["Suppression", "Rounding"]
   }

checks.json
-----------

Maps each *check* to the *evidence* it requires in order to run.

Example entry::

   "MinimumThresholdCheck": {
       "evidence": ["count_table"]
   }

How They Chain Together
------------------------

When a researcher calls ``session.crosstab(..., aggfunc="mean")``, ACRO follows this chain:

::

   "Mean"  →  analyses.json  →  statbarn: "DescriptiveStatistics"
                ↓
   statbarns.json  →  risks: ["SmallGroupRisk", "DominanceRisk", ...]
                ↓
   risks.json  →  checks: ["MinimumThresholdCheck", "NKCheck", "PPercentCheck", ...]
                ↓
   checks.json  →  evidence: ["count_table", "top_n_sum", "sum", "max", ...]

All required evidence is collected in one pass before any check runs.

The Core Classes
================

SDCChecks
----------

**Module**: ``acro.sdcchecks``

The central rule engine.  One instance is created per ACRO session and shared across
all analysis calls.

**Key responsibilities:**

* Loads and holds the four JSON knowledge files and the TRE's risk appetite.
* Provides ``get_evidence_forall_analyses(analyses, model)``  given a list of analysis
  names and a model object, returns a populated ``SDCEvidence`` instance.
* Provides ``run_checks_for_analysis(analysis_name, evidence, model)``  runs all checks
  for a given analysis and returns a ``ChecksResults``.
* Maintains a ``check_to_method`` dictionary mapping check names (strings) to the Python
  methods that implement them.

**You do not use this class directly.**  It is created inside ``ACRO.__init__()``.

TableModelDetails
-----------------

**Module**: ``acro.tablemodeldetails``

A portable description of a table-type analysis.  Created at the start of every call
to ``crosstab()``, ``pivot_table()``, ``hist()``, ``pie()``, or ``surv_func()``.

**What it stores:**

* ``index``, ``columns``, ``values``  the Series passed to the analysis command.
* ``kwargs``  all keyword arguments needed to reproduce the table.
* ``model_type``  ``"table"``, ``"array"`` (histograms, pie charts), or ``"survival"``.
* ``risk_appetite``  the TRE's thresholds (copied from ``SDCChecks``).
* ``variable_metadata``  a dictionary mapping each dimension name to its
  ``CategoricalDtype`` and URI, preserving all category values even after suppression.

**Key methods for evidence collection:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Method
     - Returns
   * - ``get_count_table()``
     - DataFrame of observation counts per cell.
   * - ``get_allfalse_table()``
     - Boolean DataFrame with all cells ``False`` (used as a base mask).
   * - ``get_zeros_table()``
     - DataFrame of zeros matching the table structure.
   * - ``get_newagg_table(aggfunc)``
     - The table rerun with a different aggregation function.
   * - ``get_dimension_names()``
     - List of dimension (categorical) variable names.
   * - ``get_variable_type_dict()``
     - Dict mapping each variable to its ontology URI
       (``DIMENSION_URI`` or ``MEASURE_URI``).

SDCEvidence
-----------

**Module**: ``acro.sdcchecks``

A data container populated by ``SDCChecks.get_evidence_forall_analyses()``.

**Attributes:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Attribute
     - Contents
   * - ``dof``
     - Residual degrees of freedom.  An integer for regression models; a
       DataFrame of per-cell (count − 1) values for table models.
   * - ``interim_tables``
     - Dict of DataFrames, keyed by evidence name (e.g. ``"count_table"``,
       ``"sum"``, ``"max"``, ``"top_n_sum"``).
   * - ``variable_type_dict``
     - Names of dependent and independent variables (supports secondary
       disclosure control review).

ChecksResults
--------------

**Module**: ``acro.sdcchecks`` (dataclass)

Returned by ``SDCChecks.run_checks_for_analysis()``.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Contents
   * - ``overall_status``
     - ``"pass"``, ``"review"``, or ``"fail"``.
   * - ``summaries``
     - Concatenated plain-English summaries from every check.
   * - ``outcomes``
     - Dict mapping check name → result (mask DataFrame or scalar).
   * - ``fair_dict``
     - Structured SDC process metadata for FAIR reporting.

ManyChecksResults
------------------

**Module**: ``acro.sdcchecks``

Wraps a dictionary of ``ChecksResults`` when a table uses multiple aggregation
functions (e.g. ``aggfunc=["mean", "std"]``).

**Key methods:**

* ``get_overall_status()``  ``"fail"`` if any analysis fails, else ``"review"``
  if any reviews, else ``"pass"``.
* ``get_overall_summary()``  concatenated summaries.
* ``get_overall_fair()``  merged FAIR dict across all analyses.
* ``get_table_sdc()``  structured SDC dict for storage in the audit record.

Suppression via Data Redaction
===============================

A key design change in v0.4.12 is *how* suppression is applied.

**Previous approach**: Apply a boolean mask to the computed table, replacing risky cells
with ``NaN``.  This made it nearly impossible to recompute marginal totals correctly
for non-additive aggregation functions (mean, median, etc.).

**New approach**: Identify which records fall into disclosive cells, **remove those records
from the data**, then **rerun the full pandas table query** on the redacted data.  Because
pandas computes margins from the data, the marginal totals are always correct.

The functions that implement this live in ``acro/table_utils.py``:

* ``get_redacted_data(data, queries, dimensions)``  removes records matching a list of
  cell queries.
* ``get_redacted_table(model, collated_assessment)``  orchestrates redaction and reruns
  ``pd.crosstab()``.
* ``get_redacted_pivottable(model, collated_assessment)``  same for ``pd.pivot_table()``.

Category Preservation
----------------------

When records are removed, any dimension (categorical) column may lose some of its
category values.  ACRO re-casts each dimension to its original ``CategoricalDtype``
after redaction, so the rerun table always has the same rows and columns as the
original.  This is handled by the ``variable_metadata`` stored in ``TableModelDetails``.

Federated Evidence Serialisation
=================================

When ``federated=True``, ACRO skips the checks locally and instead serialises the
collected evidence so it can be sent to a trusted aggregator.

The ``Records.finalise_evidence(path, evidence_store)`` method:

1. Creates the output directory.
2. For each output, writes each ``SDCEvidence.interim_table`` DataFrame to a
   separate ``{output_id}_{table_name}.csv`` file.
3. If ``dof`` is a multi-line string (i.e. a serialised DataFrame), writes it to
   ``{output_id}_dof.csv``.
4. Returns a ``evidence.json`` manifest listing every file and metadata for each output.

The aggregator can reconstruct the evidence from these files and run the checks
centrally without accessing individual-level data.

Regenerating the Knowledge Files
==================================

``acro/ontology_handler.py`` is the script used by maintainers to regenerate the four
JSON files from the live ontology.  **Researchers do not need to run this.**

The script:

1. Fetches the StatbarnsSDC ontology from ``https://ai-sdc.github.io/statbarnsdc/statbarnsdc.ttl``.
2. Parses the RDF graph.
3. Extracts statbarns, risks, checks, and analyses with their definitions and labels.
4. Writes ``analyses.json``, ``statbarns.json``, ``risks.json``, ``checks.json`` to the
   ``acro/`` directory.

TRE administrators who need to customise the knowledge base can run this script against
a locally modified ontology.

Adding a New Analysis Type
===========================

The ontology-driven architecture makes it straightforward to support new analysis types.
The steps are:

1. **Define the analysis** in the StatbarnsSDC ontology (or extend a local copy).
2. **Regenerate** the JSON files using ``ontology_handler.py``.
3. **Add a method** to the ``ACRO`` class (or ``Tables`` / ``Regression`` mixin) that:

   a. Creates a ``TableModelDetails`` instance (or uses the statsmodels model directly).
   b. Calls ``self.sdc_checks.get_evidence_forall_analyses([analysis_name], model)``.
   c. Calls ``self.sdc_checks.run_checks_for_analysis(analysis_name, evidence, model)``.
   d. Calls ``self._process_table_output(...)`` or ``self._process_analysis_output(...)``.

No changes to ``SDCChecks``, ``SDCEvidence``, or any check implementation are needed
unless the new analysis requires genuinely new evidence types.
