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
    correct_output: str = (
        '{"G":{"2010":"ok","2011":"ok","2012":"ok",'
        '"2013":"ok","2014":"ok","2015":"ok"},"N":{"2010":"ok","2011":"ok",'
        '"2012":"ok","2013":"ok","2014":"ok","2015":"ok"},"R":{"2010":"ok",'
        '"2011":"ok","2012":"ok","2013":"ok","2014":"ok","2015":"ok"},'
        '"R\\/G":{"2010":"threshold; ","2011":"threshold; ","2012":"threshold; ",'
        '"2013":"threshold; ","2014":"threshold; ","2015":"threshold; "}}'
    )
    assert output["output_0"]["outcome"] == correct_output
