import os
import sys
from datetime import datetime

# Path setup
# Ensure 'src' (package root) is importable for autodoc
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../src'))

project = 'VGNC Internal ORM'
author = 'VGNC Team'
year = datetime.now().year
copyright = f'{year}, {author}'

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]

myst_enable_extensions = [
    'colon_fence',
]

templates_path = ['_templates']
exclude_patterns = ['_build']

html_theme = 'alabaster'
html_static_path = ['_static']

# Autodoc defaults
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

# Intersphinx mapping for external references (e.g., SQLAlchemy labels/objects)
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'sqlalchemy': ('https://docs.sqlalchemy.org/en/20', None),
}

