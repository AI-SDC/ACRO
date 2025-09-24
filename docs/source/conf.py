import os
import sys

sys.path.insert(0, os.path.abspath("../../"))

from acro.version import __version__


project = "ACRO"
copyright = "2024, ACRO Project Team"
author = "ACRO Project Team"
release = __version__


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "numpydoc",
    "nbsphinx",
    "sphinx_autopackagesummary",
    "sphinx_issues",
    "sphinx_prompt",
    "pydata_sphinx_theme",
    "sphinx_design",
]

exclude_patterns = []

html_static_path = ["_static"]



html_theme = "pydata_sphinx_theme"


html_static_path = ['_static']
html_css_files = [
    'css/custom.css',
]



numpydoc_class_members_toctree = True
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}


autodoc_typehints = 'description'
autodoc_member_order = 'bysource'


html_theme_options = {
    "navigation_depth": 3,
    "show_toc_level": 2,
    "collapse_navigation": False,
    "navigation_with_keys": True
}


nbsphinx_execute = 'never'
nbsphinx_allow_errors = True


source_suffix = {
    '.rst': None,
}