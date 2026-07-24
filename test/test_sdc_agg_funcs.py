"""Unit tests for sdc aggregation functions."""

import pandas as pd
import pytest

from acro.sdc_agg_funcs import (
    agg_missing,
    agg_mode,
    agg_num_negative,
    agg_top_n_sum,
    get_statsmodel_dof,
)


def test_agg_mode_single_mode():
    """Agg_mode returns the single mode."""
    s = pd.Series([1, 2, 2, 3])
    assert agg_mode(s) == 2


def test_agg_mode_multiple_modes():
    """Agg_mode handles multiple modes by picking one randomly."""
    s = pd.Series([1, 1, 2, 2])
    result = agg_mode(s)
    assert result in (1, 2)


def test_agg_num_negative_with_negatives():
    """Agg_num_negative returns count of negatives."""
    s = pd.Series([-1, 2, -3, 4])
    assert agg_num_negative(s) == 2


def test_agg_num_negative_no_negatives():
    """Agg_num_negative returns 0 when no negatives."""
    s = pd.Series([1, 2, 3])
    assert agg_num_negative(s) == 0


def test_agg_missing_with_nan():
    """Agg_missing returns True when NaN present (line 99)."""
    s = pd.Series([1.0, float("nan"), 3.0])
    assert bool(agg_missing(s)) is True


def test_agg_missing_no_nan():
    """Agg_missing returns False when no NaN."""
    s = pd.Series([1.0, 2.0, 3.0])
    assert bool(agg_missing(s)) is False


def test_agg_top_n_sum_non_numeric():
    """Agg_top_n_sum returns 0 for non-numeric dtype."""
    s = pd.Series(["a", "b", "c"])
    assert agg_top_n_sum(s) == 0


def test_get_statsmodel_dof_no_attribute():
    """Get_statsmodel_dof raises AttributeError when model lacks df_resid."""

    class FakeModel:
        pass

    with pytest.raises(AttributeError, match="model does not have df_resid attribute"):
        get_statsmodel_dof(FakeModel())
