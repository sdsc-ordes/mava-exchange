"""Configuration file for the Sphinx documentation builder.

Full list of options can be found in the Sphinx documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

# -- Project information

project = 'mava-exchange'
copyright = '2026, SDSC'
author = 'Sabine Maennel'

# -- Configuration

extensions = [
    'sphinx.ext.autodoc',        # Extract docs from docstrings
    'sphinx.ext.autosummary',    # Generate summary tables
    'sphinx.ext.napoleon',       # Support NumPy/Google docstrings
    'sphinx.ext.intersphinx',    # Link to other docs
    'myst_parser',               # Parse Markdown
]

# Autosummary: tells Sphinx to auto-create detailed pages
autosummary_generate = True
autosummary_imported_members = False

# Autodoc: what to show by default
autodoc_default_options = {
    'members': True,              # Show all members
    'undoc-members': False,       # Hide undocumented stuff
    'special-members': False,     # Hide __special__ methods
    'exclude-members': '__weakref__, __dict__, __module__, __init__',
    'member-order': 'bysource',
}

# Enable Markdown features like tables and task lists
myst_enable_extensions = ["colon_fence", "html_image", "attrs_inline"]

templates_path = ['_templates']
exclude_patterns = []

# Tell Sphinx to look for .md files
source_suffix = {
    '.md': 'markdown',
}

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

html_theme = 'furo'
html_title = "mava-exchange"
html_static_path = ['_static']
html_theme_options = {
    "light_logo": "assets/mava_logo.svg",
    "dark_logo": "assets/mava_logo.svg",
}
# Tell Sphinx to include your custom CSS file in every page
html_css_files = [
    'styles.css',
]
html_additional_pages = {
    "mava-ontology": "mava.html",
}
