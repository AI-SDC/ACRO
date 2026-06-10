# Design brief for "ontology-driven" acro

## Rationale
1: The previous versions of the acro package suffered from a range of weaknesses, stemming from the fact that the choices of which checks needs to be run were hard-coded.
- No simple mechanism for outputting FAIR statements of which checks had been run and why
- No simple mechanism for verifying this conformed to the knowledge base embedded in the statbarns work
- Lots of work needed whenever a contributor wanted to add support for a new type of analysis.
- Some functions (especially acrotables) had become bloated to the point of being hard to understand and maintain.
- There is no easy way to provide help and descriptions of the SDC process relevant to a given analysis to a researcher.

2: The previous version of the code removed empty rows/columns from output tables which created a world of pain when applying suppression. Arguably, it also provides a vector for class disclosure and other inference attacks.

3: The previous version created suppression 'masks' which were applied to suppress tables. This made it very difficult to correctly recompute marginal totals for e.g. means/medians,...

## Chosen solution
1: The chosen solution was to read in this knowledge 'on session initiation' so that:
 code to instantiate analyses just need to specify their type according to the [statbarnsdc ontology](w3id.org/statbarnsdc). From there it is possible to unambiguously define the 'statbarn' - and hence the associated risks, checks and potential mitigations, and to call those and collate (and output) the evidence needed for risk assessment.

This has the added benefit that as thinking around SDC protocols  adapts and changes (for example, moving _histograms_ from the __Frequency_ statbarns to a new one, all that is needed is to change the formal ontology, not the code base itself.

However, TRE airlock procedures mean it is may not be  possible to read from w3id.org `on-the-fly`.
- So in practice we provide a separate program `ontology_handler.py` which captures the knowledge in 3 json-encoded lookup-tables: `analyses.json`, `risks.json` and `statbarns.json`.
- This should be run (by a code-runner action?) prior to the generation of any new release of the code, and the json files included with the pypi/Conda distributions.

- Note these `.json` files contain all the URIs and textual description of analyses, statbarns, risks, checks and mitigations, so they are present  and potentially accessible within the TRE. It is a matter for future work to decide how best to make these available to the researcher

2: We now override the default pandas settings to enforce `dropna=False` on outputs.

3: We now apply suppression by redacting the data (i.e. identify and remove records falling into _disclosive_ cells) and then re-running the table creation process. This has the benefit of using pandas functionality to correctly compute marginals for different aggregation functions.

## Implications
We have created several new classes to support this work.

![image](./classes_acro.png)

1: `TableModelDetails` : An abstract class supporting the information needed to create tabular outputs from commands such as `crosstab()`, `pivot_table()`, `pie`, `hist`, `survival` in a standardised format.

These commands all need similar information to perform SDCchecks, and runnigf some of the checks requires creating identical tables but with different aggregatino functions. Hence this class aboids lots of repeated code and type checking, and abstracts from the specifics of the different syntax, via methods such as `get_crosstab_args()`, `get_crosstab_kwargs() etc.

The class also provides attributes and methods for capturing meta-data around the 'dimensions' (e.g. the categorical factors used to define rows/columns). In turn that supports preserving the range of possible values for dimensions via  the mechanism of  pandas `CategoricalDtype`s  (and setting `observed=False`) so they are not lost when data is redacted.

2: `SDCChecks()` , with associate dataclasses `ChecksResults` and `ManyChecksResults` provides support for the main process of risk assessment.

Thus for example in a regression model we just do:
```
        ##### Step 1: build the output
        model = sm.OLS(endog, exog=exog, missing=missing, hasconst=hasconst, **kwargs)
        results = model.fit()

        ##### Step 2: identify type of output and gather evidence
        analysis_name = "GeneralLinearModel"
        checkresults: ChecksResults = self.sdc_checks.run_checks_for_analysis(
            analysis_name, model
        )
```


The added benefit of this class is that it has attributes for storing the risk appetite.
Thus an ACRO object (session) contains an instance of this class created during `acro.__init__()`
rather than holding versions of the relevant parameters in `acro_tables.py`.

3: To reduce clutter, many of the functions previously held in `acro_tables.py` are moved to a support file `table_utils.py`. There is probably plenty scope for further refactoring of this code  - for example, into a `Redact()` class - which may make the codebase easier to maintain.

## Overview of process flow

1. User starts an acro session.
    - SDCChecks() object (`self.sdc_checks`) is created and populated from (i) The risk appetite read from the config file and (ii) The contents of the analyses/statbarns/risks.json files

2. Researcher requests output e.g.a table:
 - a `TableModelDetails` instance is created to store the data, row/column/values variables, aggregation function and other parameters needed  to recreate the table.
 - The requested output is created.
 - The list of analyses requested to be reported within the table (i.e. the _aggregation functions_) is used to drive the generation of risk assessment results e.g.
```
        ##### Step 2: identify type of output and gather evidence
        analysis_names: list[str] = aggfunc_to_strings(aggfunc)
        # extra layer of loops as requested tables may have more than one agg func
        collatedres = ManyChecksResults()
        for analysis in analysis_names:
            collatedres.allchecksresults[analysis] = (
                self.sdc_checks.run_checks_for_analysis(analysis, model_details)
            )

```

- the method `run_checks_for_analysis` starts by using  the lookup tables to determine the relevant SDC details and which checks need to be run and reported:
  ```        sdc_dict = self.get_sdctokens_for_analysis(analysis_name)```

Then loops through these making calls to simple method which return appropriate masks.
```
      for check in sdc_dict["checks_needed"]:
            checkfunc = self.check_to_method[check]
            status, summary, outcome = checkfunc(analysis_name, model)
            ...
```

Finally the results (status, summary, and dictionary of masks) of the different checks are collated and returned in a `ChecksResults` dataclass object.

## TODO
Report on status of checks and where further work is needed. Not sure that belongs in this brief?
