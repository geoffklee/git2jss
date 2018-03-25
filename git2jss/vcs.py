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

""" Model for interacting with VCSs """
from __future__ import absolute_import, division, print_function
import subprocess
import tempfile
import shutil
import re
import os
import io
from git2jss.exceptions import Git2JSSError

class TagNotFoundError(Git2JSSError):
    """ Tag wasn't found """
    pass


class TooManyRemotesError(Git2JSSError):
    """ We can only handle one remote """
    pass


class NoRemoteError(Git2JSSError):
    """ There needs to be at least one remote """


class FileNotFoundError(Git2JSSError):
    """ File Not Found """
    pass


class NotAGitRepoError(Git2JSSError):
    """ Dir is not a git repo """
    pass


class GitRepo(object):
    """ Provides helper methods to interact with Git """

    def __init__(self, tag, create=False, sourcedir='.'):
        """ Create a GitRepo object which represents the
        remote repository at state `tag`

        Optionally, create tag `tag` and push it to the remote
        repository before instantiation.

        Use local repository `sourcedir` as the basis
        for working out where the Git remote is located
        (defaults to ".")
        """

        self.tag = tag
        self.sourcedir = sourcedir
        self.tmp_dir = tempfile.mkdtemp()

        try:
            self.remote_name = self._find_remote_name()

        except subprocess.CalledProcessError as err:
            if err.output.find('Not a git repository'):
                raise NotAGitRepoError(err.output)

        self.remote_url = self._find_remote_url()

        if self.has_tag_on_remote():
            self._clone_to_tmp()
        else:
            if not create:
                raise TagNotFoundError("tag doesn't exist on git remote {}: {}"
                                       .format(self.remote_url, self.tag))
            else:
                self.create_tag()
                self.__init__(tag)  # pylint: disable=non-parent-init-called

    def __del__(self):
        """ Called when there are 0 references left to this
        object
        """
        # I don't think this is the best way to do this.
        # we should be using a context manager but I don't know
        # how to make that work in this situation

        # Clean up our temp dir, cheking whether things still
        # exist first.
        if os is not None and self.tmp_dir is not None:
            if os.path.exists(self.tmp_dir):
                print("Cleaning up tmpdir {}".format(self.tmp_dir))
                shutil.rmtree(self.tmp_dir)

    def _find_remote_name(self):
        """ Find the name of the current git remote configured
        for local repository `directory`.
        Repositories with more than 1 remote are not
        currently supported.
        """
        remotes = subprocess.check_output(['git', 'remote'],
                                          cwd=self.sourcedir).strip().split('\n')

        if len(remotes) > 1:
            raise TooManyRemotesError(
                "Don't know how to handle more than 1 remote: {}".format(remotes))
        elif len(remotes) < 1 or remotes[0] == '':
            raise NoRemoteError("No Git remote is configured")

        return remotes[0]

    def _find_remote_url(self):
        """ Divine the URL of our git remote, using the
        name in self.remote_name
        """
        print("Remote: {}".format(self.remote_name))

        _url = subprocess.check_output(["git", "config", "--get",
                                        "remote." + self.remote_name +
                                        ".url"], cwd=self.sourcedir).strip()
        # Normalise URL to not end with '.git'
        if re.search(r'\.git$', _url):
            _url = _url[:-4]

        return _url

    def _clone_to_tmp(self):
        """ Check out a fresh copy of the `tag` we are going to operate on
            script_tag must be present on the git master
        """

        print("git remote: {}".format(self.remote_url))
        subprocess.check_call(["git", "clone", "-q", "--branch",
                               self.tag, self.remote_url + ".git", self.tmp_dir])

    def create_tag(self, msg='Tagged by Git2jss'):
        """ Create tag and push to git remote """
        subprocess.check_call(['git', 'tag', '-a', self.tag, '-m', msg],
                              cwd=self.tmp_dir)
        subprocess.check_call(['git', 'push', 'origin', self.tag],
                              cwd=self.tmp_dir)
        print("Tag {} pushed to git remote".format(self.tag))


    def file_info(self, filename):
        """ Return a dict of information about `filename` """
        if self.has_file(filename):
            git_info = {}
            git_info['VERSION'] = self.tag
            git_info['ORIGIN'] = self.remote_url
            git_info['PATH'] = filename
            git_info['DATE'] = subprocess.check_output(["git", "log",
                                                        "-1", '--format="%ad"',
                                                        filename], cwd=self.tmp_dir).strip()
            # git_info['USER'] = jss_prefs.user
            git_info['LOG'] = subprocess.check_output(["git", "log",
                                                       '--format=%h - %cD %ce: %n %s%n',
                                                       filename], cwd=self.tmp_dir).strip()
            return git_info
        else:
            raise FileNotFoundError("Couldn't find file {} at tag {}"
                                    .format(filename, self.tag))

    def path_to_file(self, filename):
        """ Return absolute path to `filename` inside
        our temporary directory
        """
        path = os.path.join(self.tmp_dir, filename)
        if self.has_file(filename):
            return os.path.abspath(path)
        else:
            raise FileNotFoundError("Couldn't find file {} at tag {}"
                                    .format(filename, self.tag))

    def has_file(self, filename):
        """ Return True if `filename` exists in this
        repo at this tag version, False of not
        """
        path = os.path.join(self.tmp_dir, filename)
        return os.path.isfile(os.path.abspath(path))

    def get_file(self, filename):
        """ Return an open file handle to `filename`
        """
        handle = io.open(self.path_to_file(filename), 'r', encoding="utf-8")
        return handle

    def has_tag_on_remote(self):
        """ Check whether `tag` exists in the current repo
        return True or false.
        """
        # Get tags from the git remote
        taglist = subprocess.check_output(['git', 'ls-remote', '--tags'],
                                          cwd=self.sourcedir)

        # Parse into a list of tags that exist on the git remote
        tags = [t.split('/')[-1:][0] for t in taglist.split('\n')]

        # Does tag exist?
        return self.tag in tags
