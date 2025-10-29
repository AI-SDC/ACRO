# This document describes the Stata commands currently supported by ACRO's Stata skin
We focus on Stata V17 and above as the syntax changed significantly from then, but support for Stata V16 and below is broadly the same

**If there are things you would like us to support**: please email sacro.contact@uwe.ac.uk or [add an issue to github](https://github.com/AI-SDC/ACRO/issues/new/choose)


**Author** james.smith@uwe.ac.uk
**Last Updated** October 2025

----

## Introduction and General Concepts
### AIM
ACRO is designed to provide drop-in replacements for commonly-used Stata commands that add functionality to let researchers and TRE staff fulfil their collective duty to produce _Safe Outputs_.
Most _data management_ is done exactly as before, the difference comes when you issue a _query_ that produces an output you may want to take out of the TRE.

ACRO provides automate checks against risks you should be checking such as: _small group sizes_ , _class disclosure_, _dominance_ and _low residual degrees of freedom_.
Researchers are provided with this feedback immediately  so they can choose to:  **redesign** their outputs to reduce risks, **or** apply a mitigation strategy (e.g. suppressing table cells with low counts and adjust row/column totals), **or**   request an exception if they have good cause.

### ACRO _sessions_
They key concept is that of an acro _session_ : comparable to doing a day's work and requesting some outputs at the end.
Of course you can save your work at any stage using normal Stata functionality.
We anticipate that people may want to do preparatory work, and then add _acro_ to their code and do a final run through.


### Caveat
At present most  acro-assessed outputs are saved and egressed as csv files or image files.
So we currently assume you will format your results and your paper at the time you produce the publication.
We have open issues to support more formatted work -and welcome feedback on that.

---

## ACRO session management commands

```acro init```: _starts an acro session_

```acro print_outputs```: _prints list to screen of outputs in current session and their status_

```acro remove_output output_id```:  _removes a named output from an acro session_

```acro rename_output output_id new_name```:  _renames a named output from an acro session_

```acro add_comments output_id comment_string```:  _adds a comment (string) to a named output from an acro session_

```acro add_exception output_id exception_string```:  _adds an exception request (string) comment to a named output from an acro session_

```acro finalise [output_dir] [filetype]```: _wraps up the session, writing the outputs to a named directory (default= "stata_output" ) and in json format (default) or excel._

---

## ACRO commands for creating tables
V17 and beyond we support the general table syntax.

```acro table (rowvars) (colvars) (tabvars) [if] [in] [,options]```
- specification of row,column and table variables uses Stata's syntax and (and parser)
- you can create multiple hierarchies within your rows and columns, and also separate your outputs into a set of tables
- you can have multiple statistic commands but currently these will be output `side by side` rather than underneath each other
- weights  are not currently supported within the options
- formatting commands are not currently supported within the options

---

## ACRO commands for creating regression models
``` acro regress dependent_ var independent_vars [if] [in]  ```: _linear regression_

``` acro logit dependent_ var independent_vars [if] [in] ```: _logistic regression_

``` acro probit dependent_ var independent_vars [if] [in]  ```: _probit regression_
