# What is ACRO?
ACRO is an open-source software tool for the automatic checking of research outputs and disclosure control. It helps you, as researchers, make fewer disclosive requests and the TREs spot these faster.
## Why use ACRO?
Simple: Using ACRO will help streamline the process of output checking
- So you get your research results faster
-	Giving you immediate feedback on whether your outputs are flagged as potentially disclosive
-	Providing an audited mechanism for you to:
     - add descriptions of your outputs,
     - request exceptions if you feel the strict rules-based approach is inappropriate.

## How does ACRO work?
ACRO is designed to let you use familiar commands in in R, Stata and Python. Lightweight *translation scripts*    intercept your commands and pass them through to a python ‘engine’, based on industry-standard packages that run your commands and perform statistical disclosure checks on them:
- Pandas is usually used to produce tables of results and (soon) plots.
- Statsmodels is used to provide support for regression analysis data.

The outputs from your commands, and the results of the disclosure checks can then be saved or displayed on the screen.
 This allows you to see what the output checkers will see and make changes accordingly.
 Once you are happy with your outputs ACRO lets you bundle them up with the disclosure checks, and any comments you want to send to the output checkers.

## How to use ACRO in your research scripts?
### Step 1: Start by creating an ACRO session
-	In R:  you simply import the acro module: ```source("../acro.R")  # ACRO```
-	In Stata:  ```acro init```
-	In Python: ```acro = ACRO(suppress=False)```

The suppress option lets you control whether disclosive outputs are automatically redacted.

After initialising the ACRO object the TRE risk appetite will be displayed on the screen to show you the default parameters for the disclosure tests defined by the TRE.

### Step 2: Producing your outputs with the acro prefix
All the commands for producing analyses will automatically add the output to the acro object you created in step 1.

**Tables** are made using the pandas cross_tab/pivot_table functions:
- 	In python: ```	safe_table = acro.crosstab(df.year, df.grant_type) ```
    - 	i.e., replacing ```pd.crosstab``` with ```acro.crosstab```
-	In R the corresponding command is ```acro_crosstab```.
    -	In general R commands use acro_ instead of acro as the prefix
    - We aim to build in support for  dplyer in the near future
-	in Stata: ```acro table year grant_type```
    - 	Stata commands are prefixed by acro followed by a space
    - 	We automatically translate from the standard Stata syntax (```by```, ```if```, ```in exp```, etc)

Regardless of what language you code in, the outputs from this command are:
1.	A summary of the command showing the results of the disclosure tests.
    a.	Pass which means that the output table passed all the disclosure tests.
    b.	Fail which means that one or more disclosure tests were violated.
    c.	Review which means the output needs to be checked by the output checkers - for example, if an output table has missing or negative values in one or more cells.
2.	The outcome table, showing whether each cell of the output table passed or failed the disclosure tests. If the cell failed the test, the name of the failed disclosure test will be displayed.
3.	The output table.

**Benefits to you:** In contrast  to the crosstab version of pandas which produces only the output table, the acro version allows you to check the outputs against the disclosure rules defined by the TRE. You can see the outputs from the TRE perspective and know whether the output passed all the disclosure tests or not. This will allow you to do changes to the output until it passes all the tests and is safe to be released.

**Other types of analysis** are illustrated in the notebooks on github. For example, to do a linear regression:
-	In R:
  ```reg_formula = "inc_activity ~ inc_grants + inc_donations + total_costs"```
  ```model = lm(formula= reg_formula , data=df)```
  ```summary(model)```
-	Or in Stata: ```acro regress inc_activity inc_grants inc_donations total_costs```

### Step 3: Managing your outputs
As you are editing your code ACRO lets you choose and annotate what you send to the output checkers via commands like (in python, R/Stata are equivalent)
-	To view all the research outputs that have been produced so far.
  ```results_str = acro.print_outputs()```
-	To delete outputs that are disclosive or you don’t wish to include them in the research anymore.
  ```acro.remove_output("output_1")```
-	To rename the outputs to a more descriptive name.
  ```acro.rename_output("output_2", "pivot_table")```
-	To add a text description and provide some context to the outputs. It is a way for you to communicate with the output checkers.
  ```acro.add_comments("output_0", "This is an image showing the relationship between X and Y")```
-	To add an unsupported output to the acro object without automated disclosure checking.
  ```acro.custom_output("XandY.jpg", "This image shows the relationship between X and Y")```
-	To request an exception to strict rules-bases checking.
  The exception request could include information about why you think the output should be released even though it is disclosive.
 	 For example, you may want to ask for exception if you think that some zeros are structural and don’t actually violate any rule.
  ```acro.add_exception("output_0", "This is not disclosive because … ")```

### Step 4: Call finalise() when you want to submit your work
After you are done and happy with the outputs, a call to the method ```acro.finalise(“session_name”,”json”)```  should be made.
(```acro_finalise()``` in R and ```acro finalise``` in Stata). You provide the “session name” to help you organise work between different research sessions.
The finalise function will:
1.	Check that each output with “fail” or “review” status has an exception, if not you will be asked to enter one.
-	This is to make handling exception requests an explicit part of the user experience.
-	When an output fails the checks, you will be asked to add an explanation to explain the reasons for asking to release this output despite of it being disclosive.
2.	Write the outputs to a directory. This directory contains everything that the output checkers need to make a decision. This directory contains:
-	A folder which contains the checksums for each file in the output directory.
-	The configuration file which contains the TRE risk appetite.
-	The SDC results which can be written to an Excel workbook or to a JSON file. You should choose the file format when you call finalise.
-	If the JSON format is chosen, each research output will be written to a file (typically a .csv file) and added to the output directory.

## Frequently Asked Questions
### What if I want to run my code many times before I decide exactly what to send for approval?
ACRO naturally supports this way of working. It will not produce the output folder until you are satisfied and add acro.finalise() to the end of your script.
### Why is my data exported as unformatted .csv files?
The outputs are saved in row format (as csv files) for the output checkers to check and make decisions. Although, you can change the format, if you like, the csv files should be there for the checking.
### Why is ACRO Python-based ‘under-the-hood’?
-	To ensure a consistent behaviour that can be maintained by an open-source community
-	Because there is LOTS of help available online on how to use the core analysis commands like panda.crosstab, pandas.pivot_table, and statsmodels.ols etc. commands
### Where do I get more help?
-	There are examples in the github repository: https://github.com/AI-SDC/ACRO/tree/main/notebooks
-	Documentation of all the functions is provided here: https://ai-sdc.github.io/ACRO/acro.html#acro.acro.ACRO
-	Email SACRO.contact@uwe.ac.uk

### This video shows more details for python users:

https://github.com/AI-SDC/ACRO/assets/11739683/c21a131b-d1d8-4912-b33d-09a8c7919897


### This video shows more details for R users.


https://github.com/AI-SDC/ACRO/assets/11739683/128faf5d-e89c-40d2-bb00-b7b322bb018d
