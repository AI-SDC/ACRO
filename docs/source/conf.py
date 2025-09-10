"""Configuration file for the Sphinx documentation builder."""



import os
import sys

sys.path.insert(0, os.path.abspath("../../"))

from acro.version import __version__



project = "ACRO"
copyright = "2024, ACRO Project Team"
author = "ACRO Project Team"
release = __version__



extensions = [
    "numpydoc",
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.imgconverter",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autopackagesummary",
    "sphinx_issues",
    "sphinx_prompt",
    "sphinx_rtd_theme",
]

exclude_patterns = []



html_static_path = ["_static"]



html_theme = "sphinx_rtd_theme"

html_theme_options = {
    "navigation_depth": 4,      
    "collapse_navigation": False,
    "sticky_navigation": True,    
    "includehidden": True,   
    "titles_only": False,         
    "prev_next_buttons_location": "bottom",
}


html_css_files = [
    'css/custom.css',
]


numpydoc_class_members_toctree = False