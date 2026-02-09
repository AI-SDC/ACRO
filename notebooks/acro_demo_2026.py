"""
Simple introduction to using acro for researchers.

Author: Jim Smith. 2026
"""
#!/usr/bin/env python

# # ACRO Demonstration
# This is a simple notebook to get you started with using the ```acro``` package to add disclosure risk control  to your analysis.
#
# ### Assumptions
# For the purpose of this tutorial we assume some minimal prior experience with using python for data science.
# In particular the use of the industry-standard Pandas package for:
#    -  storing and manipulating datasets
#    -  creating basic  tables, pivot_tables, and plots (e.g. histograms)
#
# This example is a Jupyter notebook split into cells.
# - Cells may contain code or text/images, and normally they are processed by stepping through them one-by-one.
# - To run (or render) a cell click the *run* icon (at the top of the page) or *shift-return* on your keyboard.
#   That will display any output created (for a code cell) and move the focus to the next cell.

# ## A: The basic concepts
# ### 1: A research _session_:
# by which we mean the activity of running a series of commands (interactively or via a script) that:
# -  ingest some data,
# -  manipulate it, and then
# -  produce (and store) some outputs.
#
# ### 2: Types of commands:
# Whether interactive, or just running a final script, we can think of the commands that get run in a session as dividing into:
# - *manipulation* commands that load and transform data into the shape you want
# - *feedback* commands that report on your data - but are never intended to be exported.
#   For example, running ```head()``` or ```describe()``` commands to make sure your manipulations have got the data into the format you want.
# -  *query* commands that produce an output from your data (table/plot/regression model etc.) that you might want to export from the Trusted Research Environment (TRE)
#
# ### 3: Risk Assessment vs decision making:
# SACRO stands for Semi-Automated Checking of Research Outputs. <br>
#  The prefix 'Semi' is important here - because it in a principles-based system humans should make _decisions_ about output requests. <br>
# To help with that we provide the SACRO-Viewer, which collates all the relevant information for them.
#
# A key part of that information is the  _Risk Assessment_.
# - Since it involves calculating metrics and comparing them to thresholds (the TRE's risk appetite) it can be done automatically, at the time an output query runs on the data.
# - This is what the ACRO tool does when you use it as part of your workflow.
#
# ### 4: What ACRO does
# The ACRO package aims to support you in producing *Safe Outputs* within minimal changes to your work flow.
# To do that we provide:
# - drop-in replacements for the most commonly used *output commands*,
#   - keeping the same syntax as the originals, and
#   - supporting as many of the options as we can (features supported will increase over time in response demand).
# - a set of *session-management* commands to help you manage the set of files you request for output.
# - **Important to note** that currently acro outputs results (tables, details of regression models etc.) as `.csv` files. <br>
#   - In other words we separate the processes of _creating_ outputs - which *must* be done *inside* the TRE.<br>
#     from the process of _formatting_ them for publication - which can be done outside the TRE with your preferred toolchain.
#   - ACRO handles creation. We are interested in hearing from researchers whether it is important to support them with formatting

# ## B: Getting Started with the demonstration
#
# ### Step 1: Setting up the environment with the tools we will use
# We will begin by importing some standard data science packages, and also the acro  package itself.

# In[ ]:

import os

import numpy as np
import pandas as pd

from acro import ACRO

# ### Step 2: Starting an ACRO session
# To do this we create an acro object by running the cell below.
#
# You can leave out the default parameters, but the cell below shows how you can:
# - provide the name of a *config* (risk appetite) file the TRE may have asked you to use
# - turn automatic suppression on or off right from the start of your session
#
# Note that when the cell runs it should report (in a different coloured font/background)
# - what version of acro is running: *this should be 0.4.12*
# - the TRE's risk appetite: that defines the rules your outputs will be checked against.
# - whether suppression is automatically applied to disclosive outputs.

# In[ ]:


acro = ACRO(config="default", suppress=False)


# ### Step 3: Loading some test data
#
# The following cells in this step just contain standard *ingestion* and *manipulation* commands to load some data into a Pandas dataframe ready to be queried.<br>
# We will use some open-source data about nursery admissions.
#
# **There is no change to your workflow here**
# - Do whatever you want in this step!
# - We just assume you end up with your data in a panda dataframe.
#
#

# In[ ]:


from scipy.io.arff import loadarff

##--- Manipulation  commands ---
# specify where the  data is
path = os.path.join("../data", "nursery.arff")

# read it in using a common dataloader
data = loadarff(path)


# store in a pandas dataframe with some manipulation of type variable names
df = pd.DataFrame(data[0])
df = df.select_dtypes([object])
df = df.stack().str.decode("utf-8").unstack()
df.rename(columns={"class": "recommendation"}, inplace=True)


# make the children variable numeric
# so we can report statistics like mean etc.

df["children"].replace(to_replace={"more": "4"}, inplace=True)
df["children"] = pd.to_numeric(df["children"])

df["children"] = df.apply(
    lambda row: (
        row["children"] if row["children"] in (1, 2, 3) else np.random.randint(4, 10)
    ),
    axis=1,
)


# In[ ]:


##--- Feedback Command ----
# show the first 5 rows to make sure everything is how we would expect
df.head()


# ## C: Producing tables that are 'Safe Outputs'
#
# The easiest way to make tables in python is to use the industry-standard pandas *crosstab()* function.
# - There are hundreds (thousands?) of web sites showing how to do this.
# - You can make (hierarchical) two-D tables (or 1-D if you add a 'dummy' variable containing the same value for each row)
# - you can specify what the table cells contain by:
#    - providing a statistic - for example: mean, count, std deviation, median etc.(pandas calls these *aggregation functions*)
#    - specifying what variable to report on
#
# The acro version uses all the pandas code - but it adds extra code that checks for disclosure risks depending on the statistic you ask for
#
# ### Example 1: A simple 2-D table of frequencies stratified by two variables
#
# Note that having imported the pandas package with the shortname `pd`(most people do)  you would normally  write
# ````
# pd.crosstab(...)
# ````
# so the only change is to use the prefix `acro.` rather than `pd.`
#
# _NB_: the first two parameters to crosstab() are mandatory, so you could just do `crosstab(df.recommendation,df.parents)` to save typing.
#
# Now run the next cell.

# In[ ]:


acro.crosstab(index=df.recommendation, columns=df.parents)


# ### How to understand this output
# The top part (with a pink background) is the risk analysis produced by acro.
# It is telling us that:
# - the overall summary is _fail_ because 4 cells are failing the 'minimum threshold' check
# - then it is showing which cells failed so you can choose how to respond
# - finally it is telling us that is has saved the table and risk assessment to our acro session with id "output_0"
#
# The part below is the normal output produced by the pandas _crosstab()_ function.
# - As this is such a small table it is not hard to spot the four problematic cells with zero or low counts
# - but of course this might be harder for a bigger table.
#
# ### How to respond to this input
# There are basically three choices:
# 1. We might decide these low numbers reveal something where the public interest outweighs the disclosure risk.<br>
# Rather than being a strict rules-based system, acro lets you attach an 'exception request' to an output, to send a message to the output checkers.<br>
# For example, you could type:
# ````
# acro.add_exception('output_0',"I think you should let me have this because...")
# ````
#
# 2. We redesign our data so that table so that none of the cells in the resulting table represent fewer than _n_ people (10 for the default risk appetite)<br>
#    For example, we could recode _'very_recommend'_ and _'priority'_ into one label.<br>
#    But maybe it is revealing that the _'recommend'_ label is not used?
#
# 3. We can redact the disclosive cells - and **acro will do this for us**.<br>
# We simply enable the option to suppress disclosive cells and re-run the query.
#
# The cell below shows option 3.
# When you run the cell below you should see that:
# - the status now changes to `review` (so the output-checker knows what has been applied)
# - the code automatically adds an exception request saying that suppression has been applied
# - and, most importantly,  the cells are redacted.

# In[ ]:


acro.enable_suppression()
acro.crosstab(index=df.recommendation, columns=df.parents)


# ## An example of a  more complex table
# Just to show off the sort of tables that `cross_tab()` can produce, let's make something more complex.<br>
# Going through the parameters in order:
# - passing a list of variable names to `index`  (rather than a single variable/column name) tells it we want a hierarchy within the rows.
#   - we can do the same to columns as well (or instead) if we want to
# - setting `values=df.children`(the name of a column in the dataset) tells it we want to report something about the number of children for each sub-group (table cell)
# - setting `aggfunc=mean` tells it the statistic we want to report is the  mean number of children (which introduces additional risks of *dominance*)
# - setting `margins=total` tells it to display row and column sub-totals
#
# It's worth noting that including the totals there are  6 columns in the risk assessment and 5 in the suppressed table. <br>
# This is because after suppression has replaced numbers with `NaN`, pandas removes the fully suppressed column (_'recommend'_) from the table.

# In[ ]:


acro.suppress = True
acro.crosstab(
    index=[df.parents, df.finance],
    columns=df.recommendation,
    values=df.children,
    aggfunc="mean",
    margins="total",
)


# ## D: What other sorts of analysis does ACRO currently support?
# We are continually adding support for more types of analysis as users prioritise them.
#
# ACRO currently supports:
# - **Tables** via `acro.crosstab()` and `acro.pivot_table()`.
#    - supported aggregation functions are:  _mean_, _median_, _sum_, _std_, _count_, and _mode_.<br>
# - **Survival analysis** via: `acro.surv_function()`, `acro.survival_table()` and `acro.survival_plot()`<br>
# - **Histograms** via:`acro.hist()` <br>
# - **Regression**  via: `acro.ols()`, `acro.logit()`,`acro.probit()`
#     with options for specifying  formula in 'R-style' by adding the suffix 'r' e.g. `acro.olsr()` etc.
#
# You can get help on using any of these using the standard python `help()` syntax as shown in the next cell

# In[ ]:


help(acro.logit)


# ## E: ACRO functionality to let users manage their outputs
# As explained above, you need to create an "acro session" whenever your code is run.
#
# After that, every time you run an acro `query' command both the output and the risk assessment are saved as part of the acro session.
#
# But we recognise that:
# - You may not want to request release of all your outputs - for example, the first table we produced above.
# - It is  good practice to provide a more informative name than just *output_n* for the .csv files that acro produces
# - It helps the output checker if you provide some comments saying what the outputs are.
# - You might want to add more things to the bundles of files you want to take out, such as:
#    - outputs from analyses that acro doesn't currently support
#    - your code itself (which many journals want)
#    - maybe a version of your paper in pdf/word format etc.
#
# Therefore acro provides the following commands for  'session management'
# ### 1: Listing the  current contents of an  ACRO session
# This output is not beautiful (there's a GUI come soon) but should let you identify outputs you want to rename,comment on, or delete

# In[ ]:


_ = acro.print_outputs()


# ### 2: Remove some ACRO outputs before finalising
# At the start of this demo we made a disclosive output -it;s the first one with status _fail_.
#
# We don't want to waste the output checker's time so lets remove it.

# In[ ]:


acro.remove_output("output_0")


# ### 3: Rename ACRO outputs before finalising
# This is an example of renaming the outputs to provide  more descriptive names.

# In[ ]:


acro.rename_output("output_1", " crosstab_recommendation_vs_parents")
acro.rename_output("output_2", "mean_children_by_parents_finance_recommendation")


# ### 4: Add a comment to output
# This is an example of adding a comment to outputs.
# It can be used to provide a description or to pass additional information to the TRE staff.<br>
# They will see it alongside your file in the output checking viewer - rather than having it in an email somewhere.

# In[ ]:


acro.add_comments(
    "mean_children_by_parents_finance_recommendation",
    "too few cases of recommend to report",
)


# ### 5. Request an exception
# An example of providing a reason why an exception should be made
# ````
# acro.add_exception("output_n", "This is evidence of systematic bias?")
# ````

# ### 6: Adding a custom output.
#
# As mentioned above you might want to request release of all sorts of things
# - including your code,
# - or outputs from analyses *acro* doesn't support (yet)
#
# In ACRO we can add a file to our session with a comment describing what it is

# In[ ]:


acro.custom_output(
    "acro_demo2026_code.py", "This is the code that produced this session"
)


# ## F: Finishing your session and producing a folder of files to release.
# This is an example of the function _finalise()_ which the users must call at the end of each session.
# - It takes each output and saves it to a CSV file (or the original file type for custom outputs)
# - It also saves the SDC analysis for each output to a json file.
# - It adds checksums for everything - so we know they've not been edited.
# - It puts them all in a folder with the name you supply.
#
# **ACRO will not overwrite previous sessions**
#
# So every time you call finalise on a session you need to either:
#   - delete the previous folder, or
#   - provide a new folder name

# In[ ]:


output = acro.finalise("my_acro_outputs_v1")


# ## G: Reminder about getting help while you work
#
# - if you remember the name of the command and want an explanation or to explain the syntax <br>
# from the python prompt type: ` help(acro.command_name)`
#
#
# - if you can't remember the name of the command, from the python prompt type: `help(acro.ACRO)`
#   - not as user friendly but will list all the available commands

# In[ ]:
