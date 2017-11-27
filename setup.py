#!python

from setuptools import setup

# Set __version__
exec(open('lib/jiradog/version.py').read())

setup(name          = 'jiradog',
      version       = __version__,

      description   = 'JIRA to DataDog processor'
      author        = 'Bryce McNab',
      author_email  = 'bmcnab@evernote.com',

      package_dir   = { '': 'lib' },
      packages      = ['jiradog'],
)
