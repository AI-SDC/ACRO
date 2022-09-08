"""Testing."""

import os

import pandas as pd

if __name__ == "__main__":
    path = os.path.join("data", "test_data.dta")
    df = pd.read_stata(path)
    print("HEAD:")
    print(df.head())

    print("CROSSTAB: year, grant_type:")
    table = pd.crosstab(df["year"], df["grant_type"])
    print(table)
