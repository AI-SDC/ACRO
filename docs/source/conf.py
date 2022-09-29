# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

sys.path.insert(0, os.path.abspath("../../"))

# -- Project information -----------------------------------------------------

project = "ACRO"
copyright = "2022, ACRO Project Team"
author = "ACRO Project Team"
release = "1.0.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "numpydoc",
    # "sphinx.ext.linkcode",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.imgconverter",
    "sphinx_gallery.gen_gallery",
    "sphinx_issues",
    # "add_toctree_functions",
    "sphinx-prompt",
    # "sphinxext.opengraph",
    # "doi_role",
    # "allow_nan_estimators",
    "matplotlib.sphinxext.plot_directive",
    "sphinx.ext.viewcode",
    # "sphinx.ext.autosummary",
    "sphinx_autopackagesummary",
    "sphinx_rtd_theme",
]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_theme_options = {"navigation_depth": 2}
