# Stata commands currently supported by ACRO
We focus on Stata V17 and above as the syntax changed significantly from then, but support for Stata V16 and below is broadly the same.

### This is an ongoing project we want to be driven by researchers' needs
So **please let us know** if there are commands or things you would like us to support:
- by emailing sacro.contact@uwe.ac.uk<br>
- or [adding an issue to github.com/ai-sdc/acro](https://github.com/AI-SDC/ACRO/issues/new/choose)


**Author** james.smith@uwe.ac.uk

**Last Updated** 11 February 2026

----

# Introduction and General Concepts
## Aim
ACRO is designed to provide drop-in replacements for commonly-used Stata commands that add functionality to let researchers and TRE staff fulfill their collective duty to produce _Safe Outputs_.

Most data management is done exactly as before, the difference comes when you issue a _query_ that produces an output you may want to take out of the TRE.

ACRO provides automated checks against risks you should be checking such as: _small group sizes_ , _class disclosure_, _dominance_ and _low residual degrees of freedom_.

Researchers are provided with this feedback immediately  so they have the power to choose between:<br>
- **redesigning** their outputs to reduce risks,
- **applying a mitigation strategy** (e.g.  acro can provide automated suppression of table cells with low counts and adjust row/column totals),
- **requesting an exception**  to strict rules-based checking.

## ACRO _sessions_
They key concept is that of an acro _session_ : comparable to doing a day's work and requesting some outputs at the end.
- Of course you can save your work at any stage using normal Stata functionality.<br>
- We anticipate that people may want to do preparatory work, and then add _acro_ prefixes to queries, and session commands to their code and do a final run through.


## Caveat
At present most  acro-assessed outputs are saved and egressed as csv files or image files.

- So **we currently assume you will format your results later** e.g.  once  they have been released from the TRE and are producing your publication.
- We have open issues to support more formatted work - and welcome feedback on that.

----


# ACRO session management commands

```acro init, config(filename)```: _starts an acro session_ using a TRE-provided risk appetite in _filename.yaml_

```acro custom_output myfilename.xxx```: _adds a custom output i.e. code, or a paper version, or images of plots or results from analyses we can't auto-check (yet)_

```acro enable_suppression```: _turns on automatic suppression for subsequent outputs_

```acro disable_suppression```: _turns off automatic suppression for subsequent outputs._

```acro print_outputs```: _prints list to screen of outputs in current session and their status_

```acro remove_output output_id```:  _removes a named output from an acro session_

```acro rename_output output_id new_name```:  _renames a named output from an acro session_

```acro add_comments output_id comment_string```:  _adds a comment (string) to a named output_

```acro add_exception output_id exception_string```:  _adds an exception request (string) comment to a named output_

```acro finalise [output_dir] [filetype]```: _wraps up the session, writing the outputs to a named directory (default= "stata_output" ) in json (default) or xlsx format.

Note that **acro will not overwrite your work**, so the name of the directory you pass to _finalise_ must not exist.<br>
You can: delete old versions manually; provide a new name; or create the name in code - for example including the date/time.<br>
The acro_demo_2026 do-file (and supporting pdfs) show how to this.


----

# ACRO commands for creating tables

For Stata versions V17 and beyond you can make tables of frequencies (or other statistics) using Stata' *table* command.

```acro table (rowvars) (colvars) (tabvars) [if] [in] [,options]```

See Stata's built-in help for details of how to use this, **and there are some simple examples at the end of this document**
- You can currently report one or more of the following statistics: _count_ (default, same as frequency), _mean_, _median_, _sum_, _std_, and _mode_.

There are some minor differences, which will be addressed in the next version.<br>
Currently not supported:
- **weights within the options**
- **formatting commands  (see above).**
- compound manipulation/query commands such creating indicator variables from categorical ones eg.<br>
    _xi: regress myvar1 i.myvar2 myvar3_<br>
    As shown in the demo you can achieve the same  effects by doing this in two steps: <br>
    _xi myvar2_ <br>
    _regress myvar1 `ds\_I*' myvar2_

----

# ACRO commands for creating regression models

``` acro regress dependent_var independent_vars [if] [in]  ```: _linear regression_

``` acro logit dependent_var independent_vars [if] [in] ```: _logistic regression_

``` acro probit dependent_var independent_vars [if] [in]  ```: _probit regression_



----


# Some simple examples of creating tables
**All of these examples are using the standard Stata syntax with the prefix _acro_**

These examples assume we have a simple data set with:
- a numerical variable _myvar_,
- and five categorical variables (_a,b,c,d,e_).
- **For simplicity** the examples below assume each categorical variable has  2 possible values.
   - e.g. _a1_ or _a2_.


## Simple two-way table of frequencies:

```acro table a b ``` produces
<div style="display: inline-block">

|  |b1|b2|
|--|--|--|
|a1|  |  |
|a2|  |  |
</div>

 where the cells contain the number of records falling into each subgroup.


## Two way table reporting statistics of variable _n_

```acro table a b, statistic(mean myvar)```

produces the table with the shape
<div style="display: inline-block">

|  |b1|b2|
|--|--|--|
|a1|  |  |
|a2|  |  |

</div>

but now the cells will contain the mean value of _myvar_ in each sub-group.
See above for aggregation functions we currently support

You can request more than one statistic - but they must refer to the same numerical variable.<br>
For example: ```acro table a b, statistic(mean myvar) statistic(std myvar)``` <br>
produces

<div style="display: inline-block">

|  | mean| |std | |
|---|---|---|---|---|
|  |b1|b2|b1|b2|
|a1|  |  |  |  |
|a2|  |  |  |  |

</div>

## Adding hierarchies and complexity to  tables
Add row or columns hierarchies by listing variables to group within parentheses.

As above, the cells will contain sub-group counts be default and other statistics on request

```acro table (a b) c``` produces
<div style="display: inline-block">


|   |   |c1 | c2|
|---|---|---|---|
|a1 | b1|   |   |
|   | b2|   |   |
|a2 | b1|   |   |
|   | b2|   |   |

</div>

```acro table a (b c)``` produces
<div style="display: inline-block">


|   |b1 |   |b2 |   |
|---|---|---|---|---|
|   |c1 |c2 |c1 |c2 |
|a1 |   |   |   |   |
|a2 |   |   |   |   |

</div>

and ```acro table (a b) (c d)``` produces
<div style="display: inline-block">

|   |   |c1 |   |c2 |   |
|---|---|---|---|---|---|
|   |   |d1 |d2 |d1 |d2 |
|a1 |b1 |   |   |   |   |
|   |b2 |   |   |   |   |
|a2 |b1 |   |   |   |   |
|   |b2 |   |   |   |   |

</div>

## Creating multiple related tables
There may be cases where you want to separate your data out
- for example if it makes the tables simpler to read

You can do this by providing a third (set of) variables alongside the row and column specifiers.

For examples ```acro table a b c``` produces:
<div style="display: inline-block">

|c1 |   |   |
|---|---|---|
|   |b1 |b2 |
|a1 |   |   |
|a2 |   |   |


|c2 |   |   |
|---|---|---|
|   |b1 |b2 |
|a1 |   |   |
|a2 |   |   |

</div>

## Even more complexity ...
As before, in multiple tables  the rows or columns  could contain hierarchies, and you can specify different statistics to report on.

So you could combine our previous  examples e.g.:<br>
``` acro table (a b) (c d) e , statistic(mean myvar) statistic(std myvar)```<br>
and so on.
