#!/usr/bin/env python

# # ACRO Tests

# In[1]:
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

# In[2]:


sys.path.insert(0, os.path.abspath(".."))


# In[3]:


from acro import ACRO, add_constant

# ### Instantiate ACRO

# In[4]:


acro = ACRO()


# ### Load test data

# In[5]:


path = os.path.join("../data", "test_data.dta")
df = pd.read_stata(path)
df.head()


# ### Pandas crosstab

# In[6]:


table = pd.crosstab(df.year, df.grant_type)
table


# ### ACRO crosstab

# In[7]:


safe_table = acro.crosstab(df.year, df.grant_type)
safe_table


# ### ACRO crosstab with aggregation function

# In[8]:


safe_table = acro.crosstab(df.year, df.grant_type, values=df.inc_grants, aggfunc="mean")
safe_table


# ### ACRO crosstab with negative values

# In[9]:


negative = df.inc_grants.copy()
negative[0:10] = -10

safe_table = acro.crosstab(df.year, df.grant_type, values=negative, aggfunc="mean")
safe_table


# ### ACRO pivot_table

# In[10]:


table = acro.pivot_table(
    df, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
)
table


# ### ACRO pivot_table with negative values

# In[11]:


df.loc[0:10, "inc_grants"] = -10

table = acro.pivot_table(
    df, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
)
table


# ### ACRO OLS

# In[12]:


new_df = df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
new_df = new_df.dropna()

y = new_df["inc_activity"]
x = new_df[["inc_grants", "inc_donations", "total_costs"]]
x = add_constant(x)

results = acro.ols(y, x)
results.summary()


# ### ACRO OLSR

# In[13]:


results = acro.olsr(
    formula="inc_activity ~ inc_grants + inc_donations + total_costs", data=new_df
)
results.summary()


# ### ACRO Probit

# In[14]:


new_df = df[["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]]
new_df = new_df.dropna()

y = new_df["survivor"].astype("category").cat.codes  # numeric
y.name = "survivor"
x = new_df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
x = add_constant(x)

results = acro.probit(y, x)
results.summary()


# ### ACRO Logit

# In[15]:


results = acro.logit(y, x)
results.summary()


# ### List current ACRO outputs

# In[16]:


acro.print_outputs()


# ### Remove some ACRO outputs before finalising

# In[17]:


acro.remove_output("output_1")
acro.remove_output("output_4")


# ### Finalise ACRO

# In[18]:


output = acro.finalise("test_results.xlsx")


# In[ ]:
