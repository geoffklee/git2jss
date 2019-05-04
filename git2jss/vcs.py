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


class RefNotFoundError(Git2JSSError):
    """ Ref wasn't found """
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

class ParameterError(Git2JSSError):
    """ Method called with unusable parameters  """
    pass

class GitRepo(object):
    """ Provides a representation of a Git repository at a particular
        point in time, with methods to retrieve files and information.
    """

    def __init__(self, tag=None, branch=None, sourcedir='.'):
        """ Create a GitRepo object which represents the
        remote repository. The remote repository will be cloned using
        the `tag` OR `branch` specified. `tag` and `branch` together
        is an error.

        :param tag: The VCS tag to use to base this object on
        :param branch: The VCS reference to use to base this object on
        :param sourcedir: (optional) The local directory from which to
            glean informaton about the remote repository. Defaults to '.'
        :rtype: vcs.GitRepo
        """

        self.tag = tag
        self.branch = branch

        if not (tag or branch):
            raise ParameterError("Specify only one of `tag` or `branch`")

        # The reference we will use to clone the repo from
        self.ref = tag or branch

        self.sourcedir = sourcedir
        self.tmp_dir = tempfile.mkdtemp()

        try:
            self.remote_name = self._find_remote_name()

        except subprocess.CalledProcessError as err:
            if err.output.find('Not a git repository'):
                raise NotAGitRepoError(err.output)

        self.remote_url = self._find_remote_url()

        if self._has_ref_on_remote(self.ref):
            self._clone_to_tmp()
        else:
            raise RefNotFoundError("Tag or branch {} doesn't exist on git remote {}"
                                   .format(self.ref, self.remote_url))

    def __del__(self):
        """ Called when there are 0 references left to this
        object. Try to delete our temporary directory.
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
        """ Clone fresh copy of the repo we are going to operate on
            self.ref must be present as a tag or branch on the git remote
        """
        print("Git remote: {}".format(self.remote_url))
        # Use check_output to suppress stdout, which is rather chatty
        # even with '-q'.
        try:
            subprocess.check_output(["git", "clone", "-q", "--branch",
                                     self.ref, self.remote_url + ".git",
                                     self.tmp_dir], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as err:
            # Don't know what happened!
            raise Git2JSSError(err.output)
        else:
            print("Checked out repo at {}.".format(self.ref))


    def _format_commit(self, filename):
        """ Return a string combining the commit ID and branch
        of `filename` to be the 'version' of a file in this repo.
        """
        commit = subprocess.check_output(["git", "log",
                                          "-1", "--format=%H",
                                          filename], cwd=self.tmp_dir).strip()

        return '{} on branch: {}'.format(commit, self.branch)

    def file_info(self, filename):
        """ Return a dict of information about `filename`
        :param filename: path to a file relative to the root of the repository
        :rtype: Dict
        """
        if self.has_file(filename):
            git_info = {}
            git_info['VERSION'] = self.tag or self._format_commit(filename)
            git_info['ORIGIN'] = self.remote_url
            git_info['PATH'] = filename
            git_info['DATE'] = subprocess.check_output(["git", "log",
                                                        "-1", '--format="%ad"',
                                                        filename], cwd=self.tmp_dir).strip()
            git_info['LOG'] = subprocess.check_output(["git", "log",
                                                       '--format=%h - %cD %ce: %n %s%n',
                                                       filename], cwd=self.tmp_dir).strip()
            return git_info
        else:
            raise FileNotFoundError("Couldn't find file {} at ref {}"
                                    .format(filename, self.ref))

    def path_to_file(self, filename):
        """ Return absolute path to `filename` inside
        our temporary directory
        :param filename: path to a file relative to the root of the
            repository
        :rtype: String
        """
        path = os.path.join(self.tmp_dir, filename)
        if self.has_file(filename):
            return os.path.abspath(path)
        else:
            raise FileNotFoundError("Couldn't find file {} at tag/branch {}"
                                    .format(filename, self.ref))

    def has_file(self, filename):
        """ Return True if `filename` exists in this
        repo at this tag/branch. False if not
        :param filename: path to a file relative to the root of the
            repository
        :rtype: Bool
        """
        path = os.path.join(self.tmp_dir, filename)
        return os.path.isfile(os.path.abspath(path))

    def get_file(self, filename):
        """ Return an open file handle to `filename`
        :param filename: path to a file relative to the root of the
            repsitory
        :rtype: File-like object
        """
        handle = io.open(self.path_to_file(filename), 'r', encoding="utf-8")
        return handle

    def _has_ref_on_remote(self, r_name):
        """ Check whether a tag or branch `r_name` exists in
        the current repo
        :rtype: Boolean
        """
        # Get refs from the git remote
        reflist = subprocess.check_output(['git', 'ls-remote', '--refs'],
                                          cwd=self.sourcedir)

        # Parse into a list of tags and branches that exist on the git remote
        refs = [t.split('\t')[-1:][0].split('/')[-1:][0] for t in reflist.split('\n')]
        # Does tag exist?
        return r_name in refs
