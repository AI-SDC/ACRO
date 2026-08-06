"""Sphinx configuration file for ACRO documentation.

This module configures the Sphinx documentation builder for the ACRO project,
including theme settings, extensions, and build parameters.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("../../"))

from acro.version import __version__


def _generate_news_rst() -> None:
    """Parse CHANGELOG.md and write docs/source/news.rst."""
    changelog = Path(__file__).parents[2] / "CHANGELOG.md"
    news_rst = Path(__file__).parent / "news.rst"

    text = changelog.read_text(encoding="utf-8")
    # Split on version headings: ## Version X.Y.Z (Date)
    sections = re.split(r"(?=^## Version )", text, flags=re.MULTILINE)

    lines = [
        "====",
        "News",
        "====",
        "",
        "Stay up to date with the latest releases across the SACRO tools family.",
        "",
        ".. note::",
        "   For the full version history, see the",
        "   `CHANGELOG <https://github.com/AI-SDC/ACRO/blob/main/CHANGELOG.md>`_.",
        "",
        "----",
        "",
    ]

    version_re = re.compile(r"^## Version (\S+) \((.+?)\)", re.MULTILINE)
    gh_base = "https://github.com/AI-SDC/ACRO/blob/main/CHANGELOG.md"

    first = True
    for section in sections:
        sec = section.strip()
        if not sec:
            continue
        m = version_re.match(sec)
        if not m:
            continue
        version, date = m.group(1), m.group(2)
        # anchor mirrors GitHub's auto-generated heading anchors
        anchor = f"version-{version.replace('.', '')}-{date.lower().replace(' ', '-').replace(',', '')}"
        gh_link = f"{gh_base}#{anchor}"

        if first:
            lines += [
                "Latest Release",
                "==============",
                "",
            ]
            first = False
        else:
            lines += [
                "----",
                "",
            ]

        lines.append(f"**ACRO v{version}** - *{date}*")
        lines.append("")
        lines.append(f"`View full changelog for v{version} \u2192 <{gh_link}>`_")
        lines.append("")

        # Convert markdown bullet lines to RST
        body = sec[m.end() :].strip()
        for raw_line in body.splitlines():
            ln = raw_line.rstrip()
            # markdown bold **text** -> RST **text** (already compatible)
            # markdown links [text](url) -> RST `text <url>`_
            ln = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"`\1 <\2>`_", ln)
            if ln.startswith(("*   ", "*  ")):
                ln = "* " + ln.lstrip("* ").strip()
            lines.append(ln)
        lines.append("")

    lines += [
        "----",
        "",
        "Other Tools",
        "===========",
        "",
        "* `SACRO-ML <https://github.com/AI-SDC/SACRO-ML>`_ - machine learning privacy tools",
        "* `ACRO-R <https://github.com/AI-SDC/ACRO-R>`_ - R language interface",
        "* `SACRO-Viewer <https://github.com/AI-SDC/SACRO-Viewer>`_ - graphical user interface",
        "",
        "Subscribe to Updates",
        "====================",
        "",
        "* Watch the `GitHub repository <https://github.com/AI-SDC/ACRO>`_ for release notifications.",
        "* Browse `GitHub Releases <https://github.com/AI-SDC/ACRO/releases>`_.",
        "* Contact the team: sacro.contact@uwe.ac.uk",
    ]

    news_rst.write_text("\n".join(lines), encoding="utf-8")


_generate_news_rst()

project = "ACRO"
copyright = "2025, SACRO Project Team"
author = "SACRO Project Team"
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


html_theme = "pydata_sphinx_theme"


html_static_path = ["_static"]
html_css_files = [
    "css/custom.css",
]


numpydoc_class_members_toctree = False
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}


autodoc_typehints = "description"
autodoc_member_order = "bysource"


html_theme_options = {"navigation_depth": 2}


nbsphinx_execute = "never"
nbsphinx_allow_errors = True


source_suffix = {
    ".rst": None,
}

suppress_warnings = ["autosummary"]
