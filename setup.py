from setuptools import setup, find_packages
from codecs import open
from os import path

__version__ = '0.1.0'

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='git2jss',
    version=__version__,
    description='Push scripts from a Git repo to a JSS. Includes templating and tagging.',
    long_description=long_description,
    url='https://github.com/gkluoe/git2jss',
    download_url='https://github.com/gkluoe/git2jss/tarball/v' + __version__,
    license='Apache Software License',
    classifiers=[
      'Development Status :: 4 - Beta',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: Apache Software License',
      'Programming Language :: Python :: 2',
    ],
    keywords='JAMF jss git release',
    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    author='Geoff Lee',
    install_requires=['python-jss', 'keyring'],
    author_email='g.lee@ed.ac.uk',
    setup_requires = ['pytest-runner'],
    tests_require = ['pytest-runner', 'pytest', 'pylint'],
    entry_points={
        'console_scripts': [
           'git2jss = git2jss.__init__:main'
          ]
    },
)
