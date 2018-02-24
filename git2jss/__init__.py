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
import sys
import subprocess
import dircache
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
TMPDIR = None

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
        print "WARNING: --all was specified so ignoring --name option"
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
    # Make TMPDIR global so that it can be used by
    # the cleanup_tmp() function, regardless of
    # when it ends up gettig called. I don't really
    # pretend to know what I'm doing, but shut up
    # pylint anyway...
    # pylint: disable=locally-disabled,global-statement
    global TMPDIR
    # pylint: disable=
    TMPDIR = make_temp_dir()

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
        print ("\n\nJSS: %s\n"
               "Username: %s\n"
               "File: %s\n\n") % (jss_prefs.url,
                                  jss_prefs.user,
                                  jss_prefs.preferences_file)
        sys.exit(0)

    if not tag_exists(options.tag):
        if options.create_tag:
            create_tag(options.tag, "Tagged by Git2JSS")
        else:
            raise Git2JSSError("Tag does not exist. If you want to create it you can "
                               "specify --create on the commandline.")

    print "Pushing tag %s to jss: %s" % (options.tag, jss_prefs.url)

    try:
        checkout_tag(options.tag)

        if options.push_all:
            files = [x for x in dircache.listdir(".")
                     if not re.match(r'^\.', x)
                     and re.match(r'.*\.(sh|py|pl)$', x)]
        else:
            files = [options.script_file]

        for script in files:
            process_script(script, options, _jss)

    except:
        print "Something went wrong."
        raise
    finally:
        cleanup_tmp()

def make_temp_dir():
    """ Create a temporary directory """
    return tempfile.mkdtemp()


def load_script(_jss, script_name):
    """ Load a script from the JSS and return a Script object """
    try:
        jss_script = _jss.Script(script_name)
    except:
        raise
    else:
        print "Loaded %s from the JSS" % script_name
        return jss_script

def process_script(script, options, _jss):
    """ Load the script from the JSS, insert the new
    code and log messages, the re-upload to the JSS
    """
    if not options.script_name:
        print "No name specified, assuming %s" % script
        jss_name = script
    else:
        jss_name = options.script_name
    try:
        print "Loading %s" % jss_name
        jss_script = load_script(_jss, jss_name)
    except jss.exceptions.JSSGetError:
        print "Skipping %s: couldn't load it from the JSS" % jss_name
        return

    script_info = get_git_info(_jss, script, options.tag)
    update_script(jss_script, script, script_info)
    save_script(jss_script)

def checkout_tag(script_tag):
    """ Check out a fresh copy of the tag we are going to operate on
        script_tag must be present on the git master
    """
    origin = subprocess.check_output(["git", "config", "--get",
                                      "remote.origin.url"]).strip()
    if re.search(r'\.git$', origin):
        origin = origin[:-4]
    try:
        print origin
        fnull = open(os.devnull, 'w')
        subprocess.check_call(["git", "clone", "-q", "--branch",
                               script_tag, origin + ".git", TMPDIR],
                              stderr=subprocess.STDOUT,
                              stdout=fnull)
    except subprocess.CalledProcessError:
        raise Git2JSSError("Couldn't check out tag %s: are you sure it exists?" % script_tag)
    else:
        return True

def tag_exists(tag):
    """ Check whether a tag exists. Returns True or false """
    tags = subprocess.check_output(['git', 'tag']).split('\n')
    return tag in tags


def create_tag(tag_name, msg):
    """ Create tag if it doesn't exist """
    if tag_exists(tag_name):
        print "Tag %s already exists" % tag_name
        raise Git2JSSError("Tag %s already exists" % tag_name)

    subprocess.check_call(['git', 'tag', '-a', tag_name, '-m', msg])
    subprocess.check_call(['git', 'push', 'origin', tag_name])

    print "Tag %s pushed to master" % tag_name


def cleanup_tmp():
    """ General cleanup tasks. """
    print "Cleaning up..."
    shutil.rmtree(TMPDIR)
    print "Cleaned up"

def update_script(jss_script, script_file, script_info, should_template=True):
    """ Update the notes field to contain the git log,
        and, if requested, template the script
    """
    # Add log to the script_info
    jss_script.find('notes').text = script_info['LOG']

    # Update the script - we need to write a base64 encoded version
    # of the contents of script_file into the 'script_contents_encoded'
    # element of the script object
    with io.open(TMPDIR + "/" + script_file, 'r', encoding="utf-8") as handle:
        if should_template:
            print "Templating script..."
            jss_script.find('script_contents_encoded').text = b64encode(
                template_script(handle.read(), script_info).encode('utf-8'))
        else:
            print "No templating requested."
            jss_script.find('script_contents_encoded').text = b64encode(
                handle.read().encode('utf-8'))

    # Only one of script_contents and script_contents_encoded should be sent
    # so delete the one we are not using.
    jss_script.remove(jss_script.find('script_contents'))


def get_git_info(jss_prefs, script_file, script_tag):
    """ Populate a dict with information about the script """
    git_info = {}
    git_info['VERSION'] = script_tag
    git_info['ORIGIN'] = subprocess.check_output(["git", "config",
                                                  "--get", "remote.origin.url"],
                                                 cwd=TMPDIR).strip()
    git_info['PATH'] = script_file
    git_info['DATE'] = subprocess.check_output(["git", "log",
                                                "-1", '--format="%ad"',
                                                script_file], cwd=TMPDIR).strip()
    git_info['USER'] = jss_prefs.user
    git_info['LOG'] = subprocess.check_output(["git", "log",
                                               '--format=%h - %cD %ce: %n %s%n',
                                               script_file], cwd=TMPDIR).strip()
    return git_info


def template_script(text, script_info):
    """ Template the script. We use a custom delimiter to
    reduce the risk of collisions """

    class JSSTemplate(Template):
        """ Template subclass with a custom delimiter """
        delimiter = '@@'

    tmpl = JSSTemplate(text)
    out = None

    try:
        out = tmpl.safe_substitute(script_info)
    except:
        print "Failed to template this script."
        raise

    return out


def save_script(jss_script):
    """ Save jss_script to the JSS """
    try:
        jss_script.save()
    except:
        print "Failed to save the script to the jss"
        raise
    else:
        print "Saved %s to the JSS." % jss_script.find('name').text
        return True


if __name__ == "__main__":
    main()
