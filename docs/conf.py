# Configuration file for the Sphinx documentation builder.
#
# OpenCHAI Manager Documentation
# https://github.com/OpenHPC-AI/OpenCHAI

import os
import sys
from datetime import datetime

# -- Path setup --------------------------------------------------------------

# Add project root to sys.path (useful if Python modules exist later)
sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------

project = "OpenCHAI Manager"
author = "OpenCHAI Community"
copyright = (
    f"{datetime.now().year}, OpenCHAI Community"
)

# Update this manually for releases
release = "1.0.0"
version = release

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "myst_parser",
]

# Allow referencing sections across files
autosectionlabel_prefix_document = True

# Support Markdown
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
    "substitution",
    "html_admonition",
    "html_image",
]

myst_heading_anchors = 3

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"

html_short_title = "OpenCHAI"
html_logo = "_static/openchai_tool_logo.png"
html_static_path = ["_static"]

html_theme_options = {
    "logo_only": True,
    "display_version": False,
    "collapse_navigation": False,
    "navigation_depth": 4,
    "sticky_navigation": True,
    "style_external_links": True,
}

html_css_files = ["custom.css"]



# -- Todo extension ----------------------------------------------------------

todo_include_todos = True

# -- Autodoc configuration ---------------------------------------------------

autodoc_member_order = "bysource"
autodoc_typehints = "description"

# -- Napoleon settings (for future Python APIs) ------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = True

# -- Intersphinx mapping -----------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- Read the Docs compatibility --------------------------------------------

# Ensures RTD builds succeed even without full environment
on_rtd = os.environ.get("READTHEDOCS") == "True"
if on_rtd:
    html_theme = "sphinx_rtd_theme"
