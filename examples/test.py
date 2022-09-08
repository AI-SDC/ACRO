"""
Testing.
Run from root with: python3 -m examples.test
"""

import os

import pandas as pd

from acro import safe_crosstab

if __name__ == "__main__":
    path = os.path.join("data", "test_data.dta")
    df = pd.read_stata(path)
    print(df.head())

    print("Pandas:")
    table = pd.crosstab(df["year"], df["grant_type"])
    print(table)

    print("Safe Pandas:")
    safe_table = safe_crosstab(df["year"], df["grant_type"])
    print(safe_table)
