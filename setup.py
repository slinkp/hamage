from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='hamagecontrol',
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Paul M. Winkler',
      author_email='slinkp@gmail.com',
      url='',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points={
          # -*- Entry points: -*-
          'hamage_filters': [
              'hamage_extlinks = hamage.filters.extlinks:ExternalLinksFilterStrategy',
              ],
          'hamage_backends': [
              'django_orm = hamage.backends.django_hamage.models:DjangoBackendFactory',
              ],
      },
    )
