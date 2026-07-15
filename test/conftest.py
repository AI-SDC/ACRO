"""Shared pytest fixtures for all tests."""

from __future__ import annotations

import os
import shutil

import pandas as pd
import pytest

from acro import ACRO

PATH: str = "RES_PYTEST"


@pytest.fixture
def cleanup_path():
    """Clean up output directories before and after each test."""
    for d in ["RES_PYTEST", "outputs", "acro_artifacts"]:
        shutil.rmtree(d, ignore_errors=True)
    yield
    for d in ["RES_PYTEST", "outputs", "acro_artifacts"]:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def data() -> pd.DataFrame:
    """Load test data."""
    path = os.path.join("data", "test_data.dta")
    return pd.read_stata(path)


@pytest.fixture
def acro() -> ACRO:
    """Initialise ACRO with suppression enabled."""
    return ACRO(suppress=True)


@pytest.fixture
def acro_federated() -> ACRO:
    """Initialise ACRO in federated mode."""
    return ACRO(federated=True)
