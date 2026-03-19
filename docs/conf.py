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
    'myst_parser',
    'sphinx.ext.extlinks',
    'sphinx.ext.autodoc',    # Pull docs from docstrings
    'sphinx.ext.napoleon',   # Support for Google/NumPy style docstrings
    'sphinx.ext.viewcode',   # Add links to highlighted source code
]

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
