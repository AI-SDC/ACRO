=============
Records Class
=============

.. currentmodule:: acro.record

The ``record`` module manages the session's output store.  It contains two classes
(``Record`` and ``Records``) and a set of module-level helper functions.

Records Class
-------------

``Records`` is the session-level container.  Every ``ACRO`` instance holds one
``Records`` object at ``acro_session.results``.

.. autoclass:: Records
   :members:
   :show-inheritance:
   :no-index:

.. note::
   **New in v0.4.12  Federated evidence serialisation:**
   :py:meth:`Records.finalise_evidence` is called by :py:meth:`acro.ACRO.finalise`
   when running in federated mode (``ACRO(federated=True)``).  It serialises each
   output's ``SDCEvidence`` interim tables to CSV files and writes an
   ``evidence.json`` manifest so a trusted aggregator can run the SDC checks
   centrally.

Record Class
------------

``Record`` represents a single output item stored in the session.

.. autoclass:: Record
   :members:
   :show-inheritance:
   :no-index:

Module-Level Functions
-----------------------

.. autofunction:: load_records
.. autofunction:: load_output
.. autofunction:: load_outcome
