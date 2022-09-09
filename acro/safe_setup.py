"""Configuration loader."""

import pathlib

import yaml
from yaml.loader import SafeLoader


def safe_setup() -> dict:
    """Returns a dictionary containing global parameters."""
    config: dict = {}
    path = pathlib.Path(__file__).with_name("default.yaml")
    with open(path, encoding="utf-8") as handle:
        config = yaml.load(handle, Loader=SafeLoader)
    return config
