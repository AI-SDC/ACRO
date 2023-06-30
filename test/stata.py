#!/usr/bin/env python
"""ACRO Stata Tests."""

# ACRO Tests

import os

import pandas as pd

from acro import ACRO, add_constant

# Instantiate ACRO

acro = ACRO()

# Load test data

path = os.path.join("../data", "test_data.dta")
df = pd.read_stata(path)
df.head()

# Pandas crosstab

table = pd.crosstab(df.year, df.grant_type)

# ACRO crosstab

safe_table = acro.crosstab(df.year, df.grant_type)

# ACRO crosstab with aggregation function

safe_table = acro.crosstab(df.year, df.grant_type, values=df.inc_grants, aggfunc="mean")

# ACRO crosstab with negative values

negative = df.inc_grants.copy()
negative[0:10] = -10

safe_table = acro.crosstab(df.year, df.grant_type, values=negative, aggfunc="mean")

# ACRO pivot_table

table = acro.pivot_table(
    df, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
)

# ACRO pivot_table with negative values

df.loc[0:10, "inc_grants"] = -10

table = acro.pivot_table(
    df, index=["grant_type"], values=["inc_grants"], aggfunc=["mean", "std"]
)

# ACRO OLS

new_df = df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
new_df = new_df.dropna()

y = new_df["inc_activity"]
x = new_df[["inc_grants", "inc_donations", "total_costs"]]
x = add_constant(x)

results = acro.ols(y, x)
results.summary()

# ACRO OLSR

results = acro.olsr(
    formula="inc_activity ~ inc_grants + inc_donations + total_costs", data=new_df
)
results.summary()

# ACRO Probit

new_df = df[["survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs"]]
new_df = new_df.dropna()

y = new_df["survivor"].astype("category").cat.codes  # numeric
y.name = "survivor"
x = new_df[["inc_activity", "inc_grants", "inc_donations", "total_costs"]]
x = add_constant(x)

results = acro.probit(y, x)
results.summary()

# ACRO Logit

results = acro.logit(y, x)
results.summary()

# List current ACRO outputs

acro.print_outputs()

# Remove some ACRO outputs before finalising

acro.remove_output("output_1")
acro.remove_output("output_4")

# Finalise ACRO

output = acro.finalise("test_results.xlsx")
