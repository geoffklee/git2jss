#!/usr/bin/env python
# Copyright (C) 2018 Geoff Lee <g.lee@ed.ac.uk>
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
from string import Template
from base64 import b64encode
import jss
from .jss_keyring import KJSSPrefs
from .vcs import GitRepo


DESCRIPTION = """A tool to update scripts on the JSS to match a tagged release in a Git repository.

The tool can create a new tag, or push scripts from an existing tag.

The 'notes' field of the JSS script object will contain the Git log for the corresponding
Script file. Some templating is also carried out.

You need to have the jss-python module installed and configured appropriately to talk to your JSS.
MANY thanks to sheagcraig for that module:  https://github.com/sheagcraig/python-jss

TEMPLATING: The following fields, if present in the script file, will be templated with values from Git

@@DATE Date of last change
@@VERSION The name of the TAG this file was pushed from
@@ORIGIN Origin URL from Git config
@@PATH The path to the script file relative to the root of the Git repo
@@USER JSS Username used to push the script (from jss-python configuration)

"""


EPILOG = """
"""

VERSION = "0.1.0"

class Git2JSSError(BaseException):
    """ Generic error class for this script """
    pass

def _get_args():
    """ Parse arguments from the commandline and return something sensible """

    parser = argparse.ArgumentParser(usage=('git2jss [-i --jss-info] [-h] [--create] '
                                            '[ --no-keychain] [--all | --file FILE '
                                            '[ --name NAME ] ] --tag TAG'),
                                     version=VERSION, description=DESCRIPTION, epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-i', '--jss-info', action='store_true', dest='jss_info',
                        help="Show information about the currently configured JSS")

    parser.add_argument('--tag', metavar='TAG', type=str, default=False,
                        help=('Name of the TAG in Git. The tag must have been pushed to origin: '
                              'locally committed tags will not be accepted.'))

    parser.add_argument('--name', metavar='NAME', dest='script_name', type=str,
                        help=('Name of the script object in the JSS (if omitted, it is assumed '
                              'that the script object has a name exactly matching FILE)'))

    parser.add_argument('--create', action='store_true', default=False, dest='create_tag',
                        help="If TAG doesn't exist, then create it and push to the server")

    parser.add_argument('--no-keychain', action='store_true', default=False, dest='no_keychain',
                        help=('Do not store authentication credentials in the system keychain.\n'
                              'To use this option, you need to manually enter the password into '
                              'the preferences file. You probably do not want to do this.'))

    file_or_all = parser.add_mutually_exclusive_group()

    file_or_all.add_argument('--file', metavar='FILE', dest='script_file', type=str,
                             help='File containing the script to push to the JSS')

    file_or_all.add_argument('--all', action='store_true', default=False, dest='push_all',
                             help=('Push every file in the current directory which has '
                                   'a matching script object on the JSS'))

    options = parser.parse_args()

    # --name doesn't make any sense with --all, but argparse won't
    # let us express that with groups, so add in a hacky check here
    if options.push_all and options.script_name:
        print("WARNING: --all was specified so ignoring --name option")
        options.script_name = None

    # Unless we've only been asked for JSS info, we need a tag to do anything
    if not options.jss_info and not options.tag:
        parser.error("Which tag do you want to push? Please specify with '--tag'")

    # We need to know which files to operate on!
    if options.tag and not (options.script_file or options.push_all):
        parser.error("You need to specify either a filename "
                     "(--file FILE) or all files (--all)")

    return options

def main():
    """ Main function """
    options = _get_args()

    if jss.tools.is_osx():
        prefs_file = os.path.join('~', 'Library', 'Preferences',
                                  'com.github.gkluoe.git2jss.plist')
    elif jss.tools.is_linux():
        prefs_file = os.path.join("~", "." + 'com.github.gkluoe.git2jss.plist')


    if options.no_keychain:
        jss_prefs = jss.JSSPrefs(preferences_file=prefs_file)
    else:
        # Use our subclass for keychain support
        jss_prefs = KJSSPrefs(preferences_file=prefs_file)

    # Create a new JSS object
    _jss = jss.JSS(jss_prefs)

    # If '--jss-info' was requested, just give the information
    if options.jss_info:
        print_jss_info(jss_prefs)
        sys.exit(0)

    _repo = GitRepo(options.tag, create=options.create_tag)

    try:
        if options.push_all:
            files = list_matching_files(".", pattern=r'.*\.(sh|py|pl)$')
        else:
            files = [options.script_file]

        for script in files:
            process_script(script, options, _jss, _repo)
    finally:
        # Try to make sure the git repo tmpdir is
        # cleaned up.
        _repo.__del__()


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


def load_jssobj(_jss, name, obj_type):
    """ Load object `name` of type `type` from the
    JSS and return it
    """
    try:
        # Calls _jss.'obj_type'(): eg _jss.Script()
        jss_script = getattr(_jss, obj_type)(name)
    except:
        raise
    else:
        print("Loaded %s from the JSS" % name)
        return jss_script


def process_script(script, options, _jss, _repo):
    """ Load the script from the JSS, insert the new
    code and log messages, the re-upload to the JSS
    """
    if not options.script_name:
        print("No name specified, assuming %s" % script)
        jss_name = script
    else:
        jss_name = options.script_name
    try:
        print("Loading %s" % jss_name)
        jss_script = load_jssobj(_jss, jss_name, 'Script')
    except jss.exceptions.JSSGetError:
        print("Skipping %s: couldn't load it from the JSS" % jss_name)
        return

    script_info = _repo.file_info(script)
    update_script(jss_script, script, script_info, _repo)
    save_script(jss_script)


def update_script(jss_script, script_file, script_info, _repo, should_template=True):
    """ Update the notes field to contain the git log,
        and, if requested, template the script
    """
    # Add log to the script_info
    jss_script.find('notes').text = script_info['LOG']

    # Update the script - we need to write a base64 encoded version
    # of the contents of script_file into the 'script_contents_encoded'
    # element of the script object
    handle = _repo.get_file(script_file)
    if should_template:
        print("Templating script...")
        jss_script.find('script_contents_encoded').text = b64encode(
            template_script(handle, script_info).encode('utf-8'))
    else:
        print("No templating requested.")
        jss_script.find('script_contents_encoded').text = b64encode(
            handle.read().encode('utf-8'))

    # Only one of script_contents and script_contents_encoded should be sent
    # so delete the one we are not using.
    jss_script.remove(jss_script.find('script_contents'))


def template_script(handle, script_info):
    """ Template the script. Pass in an open
        file handle and receive a string containing
        the templated text. We use a custom delimiter to
        reduce the risk of collisions
    """

    class JSSTemplate(Template):
        """ Template subclass with a custom delimiter """
        delimiter = '@@'

    text = handle.read()
    tmpl = JSSTemplate(text)
    out = None
    try:
        out = tmpl.safe_substitute(script_info)
    except:
        print("Failed to template this script.")
        raise

    return out


def save_script(jss_script):
    """ Save jss_script to the JSS """
    try:
        jss_script.save()
    except:
        print("Failed to save the script to the jss")
        raise
    else:
        print("Saved %s to the JSS." % jss_script.find('name').text)
        return True


if __name__ == "__main__":
    main()
