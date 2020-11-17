# -*- coding: utf-8 -*-
#
# sat documentation build configuration file, created by
# sphinx-quickstart on Fri Apr 13 10:08:59 2018.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os


# https://stackoverflow.com/questions/23462494/how-to-add-a-custom-css-file-to-sphinx
# this needs realpath(custom), cause problem on relocated git clone, 
# so use file link instead in _themes/alabaster: ln -s ../../../../src/custom.css custom.css
# def setup(app):
#     custom = os.path.join('src', 'custom.css')
#     print "setup add_stylesheet\n  %s as\n  %s" % (custom, os.path.realpath(custom))
#     app.add_stylesheet(os.path.realpath(custom))

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.mathjax', 'sphinx.ext.viewcode']

# do not use rst_prolog please use doc/rst_prolog.rst and '.. include:: ../rst_prolog.rst'
# https://github.com/sphinx-doc/sphinx/issues/2445

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'salomeTools'
copyright = u'2019, CEA'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '5.7'
# The full version, including alpha/beta/rc tags.
release = '5.7.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# default sphinxdoc scrolls agogo traditional nature haiku
html_theme = 'alabaster' #added in _theme dir

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    #'logo': 'logo.png',
    #'github_user': 'bitprophet',
    #'github_repo': 'alabaster',
    #'description': 'MYYY DESCRIPTION',
    #'sidebar_includehidden': True,
    #'sidebar_collapse': True,
    #'show_powered_by': False,
    'show_related': True,
    'fixed_sidebar': False,
    'page_width': '1000px',
    'sidebar_width': '250px',
    'font_size': '0.9em', #'1.0625em',
    'code_font_size': '0.8em',
    #'note_bg': '#eee',
    'pre_bg': '#fee', # code-block background
    #'gray_1': '#00f',
    #'gray_2': '#f00',
    #'gray_3': '#0f0',
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ["../_themes/alabaster", ]

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "images/sat_v5.png"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = ""

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = False

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'salomeToolsdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
  # The paper size ('letterpaper' or 'a4paper').
  'papersize': 'a4paper',

  # The font size ('10pt', '11pt' or '12pt').
  'pointsize': '10pt',

  # Additional stuff for the LaTeX preamble.
  #'preamble': '',

  # http://www.sphinx-doc.org/en/master/latex.html
  'sphinxsetup': 'verbatimwithframe=false, VerbatimColor={rgb}{.98,.94,.94}',
}


# The paper size ('letter' or 'a4').
#latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'salomeTools.tex', u'SAT Documentation',
   u'CEA DES/ISAS/DM2S/STMF/LGLS', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
latex_show_pagerefs = True

# If true, show URL addresses after external links.
latex_show_urls = 'footnote' # sphinx version 1.7 # True

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'salometools', u'SAT Documentation',
     [u'CEA DES/ISAS/DM2S/STMF/LGLS'], 1)
]


