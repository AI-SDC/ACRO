"""This module contains unit tests."""

import os

import pandas as pd

from acro import ACRO


def test():
    """First test."""
    # instantiate ACRO
    acro = ACRO()
    # load test data
    path = os.path.join("data", "test_data.dta")
    data = pd.read_stata(path)
    # ACRO crosstab
    _ = acro.crosstab(data["year"], data["grant_type"])
    # finalise
    output: dict = acro.finalise()
    assert output["output_0"]["outcome"] == "fail; suppression applied"
