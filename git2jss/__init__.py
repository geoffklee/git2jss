#!/usr/bin/env python
# Copyright (C) 2019 Geoff Lee <g.lee@ed.ac.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" git2jss: synchronise JSS scripts with a Git tag """
from __future__ import absolute_import, division, print_function
import sys
import subprocess
import os
import io
import re
import argparse
import tempfile
import shutil
import xml
from string import Template
from base64 import b64encode
import jss
import git2jss.processors as processors
from .jss_keyring import KJSSPrefs
from .vcs import GitRepo
from .exceptions import Git2JSSError



DESCRIPTION = """A tool to update scripts on the JSS to match a tag or the head
of a branch in a Git repository.

The tool can push scripts from an existing tag or from the head of any branch

The 'notes' field of the JSS script object will contain the Git log for the corresponding
Script file. Some templating is also carried out.

You need to have the jss-python module installed and configured appropriately to talk to your JSS.
MANY thanks to sheagcraig for that module:  https://github.com/sheagcraig/python-jss

TEMPLATING: The following fields, if present in the script file, will be templated with values from Git

@@DATE Date of last change
@@VERSION The name of the TAG this file was pushed from, or the commit ID combined with BRANCH
@@ORIGIN Origin URL from Git config
@@PATH The path to the script file relative to the root of the Git repo
@@USER JSS Username used to push the script (from jss-python configuration)

"""


EPILOG = """
"""

VERSION = "2.0.0"

# List of processors that we support - each is a class in the
# `processors` module
PROCESSORS = ['Script', 'ComputerExtensionAttribute']

def _get_args(argv=None):
    """ Parse arguments from the commandline and return an object containing them """

    parser = argparse.ArgumentParser(usage=('git2jss [-v --version] [-i --jss-info] [-h] '
                                            '[ --mode MODE ] [ --no-keychain ] '
                                            '[ --prefs-file ] (--all | --file FILE '
                                            '[ --name NAME ])  (--tag TAG | --branch BRANCH)'),
                                     description=DESCRIPTION, epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-v', '--version', action='version', version=VERSION,
                        help='Display the version and exit')

    parser.add_argument('-i', '--jss-info', action='store_true', dest='jss_info',
                        help="Show information about the currently configured JSS")

    parser.add_argument('--tag', metavar='TAG', type=str, default=None,
                        help=('Name of the tag on the git remote to operate from.'
                              'The tag must have been pushed to the remote: '
                              'locally committed tags will not be accepted.'))

    parser.add_argument('--branch', metavar='BRANCH', type=str, default=None,
                        help=('An branch on the git remote operate from.'
                              'eg: develop.'
                              'The head of the branch will be checked out and used as'
                              'the source for "--file"'))

    parser.add_argument('--mode', metavar='MODE', type=str, choices=PROCESSORS,
                        dest='mode', default='Script',
                        help=('Mode of operation. Use this option to operate on different types '
                              'of JSS object. Currently supported values are: {}.\nDefaults to '
                              '"Script"'
                              .format("\n".join(PROCESSORS))))

    parser.add_argument('--name', metavar='NAME', dest='target_name', type=str, default=None,
                        help=('Name of the target object in the JSS (if omitted, it is assumed '
                              'that the target object has a name exactly matching FILE)'))

    parser.add_argument('--no-keychain', action='store_true', default=False, dest='no_keychain',
                        help=('Do not store authentication credentials in the system keychain. '
                              'Instead, store them IN PLAINTEXT in the preferences file.\n'
                              'Be careful with this option - it could be useful in CI/CD '
                              'environments.'))

    parser.add_argument('--local-repo', metavar='LOCAL_REPO', dest='local_repo', type=str,
                        default='.',
                        help=('Path to the locally checked-out copy of the git repo you want '
                              'to work on'))

    parser.add_argument('--prefs-file', metavar='PLIST', default=None, dest='prefs_file',
                        help=(('Specify a preferences file to use. You can use this option'
                               'to talk to multiple separate JamfPro servers')))

    file_or_all = parser.add_mutually_exclusive_group()

    file_or_all.add_argument('--file', metavar='FILE', dest='source_file', type=str,
                             help='File in the Git repo containing the script to push to the JSS')

    file_or_all.add_argument('--all', action='store_true', default=False, dest='push_all',
                             help=('Push every file in the Git repo for which there is an '
                                   'object with a matching name in the JSS.'))


    options = parser.parse_args(argv)

    # --name doesn't make any sense with --all, but argparse won't
    # let us express that with groups, so add in a hacky check here
    if options.push_all and options.target_name:
        print("WARNING: --all was specified so ignoring --name option")
        options.target_name = None

    # Unless we've only been asked for JSS info, we need a tag or branch to do anything
    if not options.jss_info and (not (options.branch or options.tag)):
        parser.error(("Which tag or branch HEAD do you want to push?\n"
                      "Please specify with '--tag' or '--branch'"))

    # Can't specify --branch and --tag
    if options.branch and options.tag:
        parser.error(
            "Please specify --branch or --tag, but not both!")

    # We need to know which files to operate on!
    if (options.tag or options.branch) and not (options.source_file or options.push_all):
        parser.error("You need to specify either a filename "
                     "(--file FILE) or all files (--all)")

    return options

def main(argv=None, prefs_file=None):
    """ Main function """
    options = _get_args(argv)

    prefs_file = prefs_file or options.prefs_file or find_prefs_file()

    target_type = set_mode(options)

    try:
        if options.no_keychain:
            jss_prefs = jss.JSSPrefs(preferences_file=prefs_file)
        else:
            # Use our subclass for keychain support
            jss_prefs = KJSSPrefs(preferences_file=prefs_file)
    except xml.parsers.expat.ExpatError as err:
        raise Git2JSSError("Preferences file {} invalid: {}".format(prefs_file, err))

    # Create a new JSS object
    _jss = jss.JSS(jss_prefs)

    # If '--jss-info' was requested, just give the information
    if options.jss_info:
        print_jss_info(jss_prefs)
        sys.exit(0)

    _repo = GitRepo(tag=options.tag, branch=options.branch, sourcedir=options.local_repo)

    try:
        if options.push_all:
            files = list_matching_files(options.local_repo, pattern=r'.*\.(sh|py|pl)$')
        else:
            files = [options.source_file]
        for this_file in files:
            # Work out which type of processor to use
            processor_type = getattr(processors, target_type)

            # Instantiate the processor
            processor = processor_type(repo=_repo, _jss=_jss,
                                       source_file=this_file,
                                       target=options.target_name)

            processor.update()
            processor.save()
    finally:
        # Make sure the repo tmpdir is
        # cleaned up.
        _repo.__del__()


def set_mode(options):
    """ Select a processor to use """
    mode = options.mode
    print("Running in {} mode".format(mode))
    return mode


def find_prefs_file():
    """ Return the platform-specific location of our prefs file """
    if jss.tools.is_osx():
        prefs_file = os.path.join('~', 'Library', 'Preferences',
                                  'com.github.gkluoe.git2jss.plist')
    elif jss.tools.is_linux():
        prefs_file = os.path.join("~", "." + 'com.github.gkluoe.git2jss.plist')

    return prefs_file


def print_jss_info(jss_prefs):
    """ Print info about the currrently configured JSS
    """
    print(("\nJSS: {}\n"
           "Username: {}\n"
           "File: {}\n").format(jss_prefs.url,
                                jss_prefs.user,
                                jss_prefs.preferences_file))


def list_matching_files(directory, pattern=r'.*\.(sh|py|pl)$'):
    """ Return a list of filenames in `directory`
    which match `pattern` """
    return [x for x in os.listdir(directory)
            if not re.match(r'^\.', x)
            and re.match(pattern, x)]


if __name__ == "__main__":
    main()
