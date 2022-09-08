"""Testing."""

import os
import pandas

if __name__ == "__main__":
    path = os.path.join("data", "test_data.dta")
    data = pandas.read_stata(path)
    print(data.head())
