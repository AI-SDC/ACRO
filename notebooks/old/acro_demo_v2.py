"""ACRO Demonstration."""

# # ACRO Demonstration

# In[1]:

import os

import numpy as np
import pandas as pd

# In[2]:
# uncomment this line if acro is not installed
# ie you are in development mode
# sys.path.insert(0, os.path.abspath(".."))
# In[3]:
from acro import ACRO, add_constant

# ### Instantiate ACRO

# In[4]:


acro = ACRO(suppress=False)


# ### Load test data
# The dataset used in this notebook is the nursery dataset from OpenML.
# - In this version, the data can be read directly from the local machine after it has been downloaded.
# - The code below reads the data from a folder called "data" which we assume is at the same level as the folder where you are working.
# - The path might need to be changed if the data has been downloaded and stored elsewhere.
#  - for example use:
#     path = os.path.join("data", "nursery.arff")
#     if the data is in a sub-folder of your work folder

# In[5]:


from scipy.io.arff import loadarff

path = os.path.join("../data", "nursery.arff")
data = loadarff(path)
df = pd.DataFrame(data[0])
df = df.select_dtypes([object])
df = df.stack().str.decode("utf-8").unstack()
df.rename(columns={"class": "recommend"}, inplace=True)
df.head()


# # Examples of producing tabular output
# We rely on the industry-standard package **pandas** for tabulating data.
# In the next few examples we show:
# - first, how a researcher would normally make a call in pandas, saving the results in a variable that they can view on screen (or save to file?)
# - then how the call is identical in SACRO, except that:
#   - "pd" is replaced by "acro"
#   - the researcher immediately sees a copy of what the TRE output checker will see.
#

# ### Pandas crosstab
# This is an example of crosstab using pandas.
# We first make the call, then the second line print the outputs to screen.

# In[6]:


table = pd.crosstab(df.recommend, df.parents)
print(table)


# ### ACRO crosstab
# - This is an example of crosstab using ACRO.
# - The INFO lines show the researcher what will be reported to the output checkers.
# - Then the (suppressed as necessary) table is shown via the print command as before.

# In[7]:


safe_table = acro.crosstab(
    df.recommend, df.parents, rownames=["recommendation"], colnames=["parents"]
)
print(safe_table)


# ### ACRO crosstab with suppression
# - This is an example of crosstab with suppressing the cells that violate the disclosure tests.
# - Note that you need to change the value of the suppress variable in the acro object to True. Then run the crosstab command.
# - If you wish to continue the research while suppressing the outputs, leave the suppress variable as it is, otherwise turn it off.

# In[8]:


acro.suppress = True

safe_table = acro.crosstab(df.recommend, df.parents)
print(safe_table)


# ## An example of a  more complex table
# - make the children variable numeric
# - so we can report statistics like mean etc.
# ### Note how we don't need to use the acro prefix when we are just manipulating data

# In[9]:


df["children"].replace(to_replace={"more": "4"}, inplace=True)
df["children"] = pd.to_numeric(df["children"])

df["children"] = df.apply(
    lambda row: (
        row["children"] if row["children"] in (1, 2, 3) else np.random.randint(4, 10)
    ),
    axis=1,
)


# ### So lets make a more complex table with:
# - a hierarchy in the rows (type of parents and finance)
# -  columns for the recommendation
# - in the cells are the mean values of the children for each subgroup
# - in the margins are the total values for each row/column

# In[10]:


acro.suppress = False
acro.crosstab(
    index=[df.parents, df.finance],
    columns=[df.recommend],
    values=df.children,
    aggfunc="mean",
    margins=True,
)


# In[ ]:


# # Regression examples using ACRO
#
# Again there is an industry-standard package in python, this time called **statsmodels**.
# - The examples below illustrate the use of the ACRO wrapper standard statsmodel functions
# - Note that statsmodels can be called using an 'R-like' format (using an 'r' suffix on the command names)
# - most statsmodels functiobns return a "results object" which has a "summary" function that produces printable/saveable outputs
#
# ### Start by manipulating the nursery data to get two numeric variables
# - The 'recommend' column is converted to an integer scale

# In[17]:


df["recommend"].replace(
    to_replace={
        "not_recom": "0",
        "recommend": "1",
        "very_recom": "2",
        "priority": "3",
        "spec_prior": "4",
    },
    inplace=True,
)
df["recommend"] = pd.to_numeric(df["recommend"])

new_df = df[["recommend", "children"]]
new_df = new_df.dropna()


# ### ACRO OLS
# This is an example of ordinary least square regression using ACRO.
# - Above recommend column was converted form categorical to numeric.
# - Now we perform a the linear regression between recommend and children.
# - This version includes a constant (intercept)
# - This is just to show how the regression is done using ACRO.
# - **No correlation is expected to be seen by using these variables**

# In[18]:


y = new_df["recommend"]
x = new_df["children"]
x = add_constant(x)

results = acro.ols(y, x)
results.summary()


# ## Other supported types of queries:
# - probit regression
# - logit regression
# - regression variants using R-style definition for equations
# - survival analysis (Kaplan-Meier)
# - Histograms
# - various other ways of making tables
# -

# ### 5: Add an unsupported output to the list of outputs
# This is an example to add an unsupported outputs (such as images) to the list of outputs

# In[29]:


acro.custom_output(
    "XandY.jpeg", "This output is an image showing the relationship between X and Y"
)


# In[ ]:


# # ACRO functionality to let users manage their outputs
#
# ### 1: List current ACRO outputs
# This is an example of using the print_output function to list all the outputs created so far

# In[11]:


_ = acro.print_outputs()


# ### 2: Remove some ACRO outputs before finalising
# This is an example of deleting some of the ACRO outputs.
# The name of the output that needs to be removed should be passed to the function remove_output.
# - The output name can be taken from the outputs listed by the print_outputs function,
# - or by listing the results and choosing the specific output that needs to be removed

# In[12]:


acro.remove_output("output_0")


# ### 3: Rename ACRO outputs before finalising
# This is an example of renaming the outputs to provide a more descriptive name.

# In[13]:


acro.rename_output("output_1", "cross_tabulation")


# ### 4: Add a comment to output
# This is an example to add a comment to outputs.
# It can be used to provide a description or to pass additional information to the output checkers.

# In[14]:


acro.add_comments(
    "cross_tabulation", "Suppression has been applied. Please let me have this data."
)


# ### 5. Request an exception
# An example of providing a reason why an exception should be made

# In[15]:


acro.add_exception("output_2", "This is evidence of systematic bias?")


# ## 5: (the big one) Finalise ACRO
# This is an example of the function _finalise()_ which the users must call at the end of each session.
# - It takes each output and saves it to a CSV file.
# - It also saves the SDC analysis for each output to a json file or Excel file
#   (depending on the extension of the name of the file provided as an input to the function)
# - If an output is flagged as potentially disclosive then the
#   researcher is prompted to provide a reason for release if they have not already done so.

# In[16]:


output = acro.finalise("Examples", "json")


# In[ ]:
