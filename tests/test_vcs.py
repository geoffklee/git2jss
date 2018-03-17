""" Tests for the vcs module """
import subprocess
import os
import pytest
from pytest import raises
import git2jss.vcs as vcs

TEST_REPO = "https://github.com/gkluoe/git2jss"

@pytest.fixture(scope="session")
def gitrepo(tmpdir_factory):
    tmp_dir = str(tmpdir_factory.mktemp('gitrepo'))
    _build_local_repo(tmp_dir, remote=TEST_REPO)
    return vcs.GitRepo(tag='v0.1.0',
                       sourcedir=tmp_dir)


def _build_local_repo(test_dir, remote=None):
    """ Build a fresh local git repo.
    if `remote` is specified, add it
    to the repo
    """
    subprocess.call(["git", "init", "."],
                    cwd=test_dir)
    if remote:
        subprocess.call(["git", "remote",
                         "add", "origin",
                         remote], cwd=test_dir)


def test_new_gitrepo_not_a_repo(tmpdir):
    """ Directory is not a git repo """
    with raises(vcs.NotAGitRepoError):
        repo = vcs.GitRepo(tag='NotATag',
                           sourcedir=str(tmpdir))


def test_new_no_remote(tmpdir):
    """ Directory has no git remotes configured """
    _build_local_repo(str(tmpdir))
    with raises(vcs.NoRemoteError):
        repo = vcs.GitRepo(tag='NotATag',
                           sourcedir=str(tmpdir))


def test_too_many_remotes(tmpdir):
    """ Directory has too many remotes configured """
    _build_local_repo(str(tmpdir),
                      remote=TEST_REPO)
    # Add another remote
    subprocess.call(["git", "remote",
                     "add", "notherone",
                     "http://example.com"],
                     cwd=str(tmpdir))

    with raises(vcs.TooManyRemotesError):
        repo = vcs.GitRepo(tag='NotATag',
                           sourcedir=str(tmpdir))


def test_new_no_tag_on_remote(tmpdir):
    """ Remote doesn't have our tag """
    _build_local_repo(str(tmpdir),
                      remote=TEST_REPO)
    with raises(vcs.TagNotFoundError):
        repo = vcs.GitRepo(tag='NotATag',
                           sourcedir=str(tmpdir))


def test_new_ok(gitrepo):
    """ Successfully instantiate a GitRepo """
    assert gitrepo.remote_url == "https://github.com/gkluoe/git2jss"
    assert gitrepo.remote_name == "origin"
    assert gitrepo.tag == "v0.1.0"



def test_check_path_to_file(gitrepo):
    assert (gitrepo.path_to_file("README.rst") == 
            os.path.join(gitrepo.tmp_dir, 'README.rst'))

    assert (gitrepo.path_to_file("././././././README.rst") == 
            os.path.join(gitrepo.tmp_dir, 'README.rst'))


def test_check_non_existing_file(gitrepo):
    with raises(vcs.FileNotFoundError):
        assert gitrepo.path_to_file("kf/dsd/fsd/fs/sd.blah")


