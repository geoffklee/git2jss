""" Tests for the vcs module """
# --*-- encoding: utf-8 --*--
import subprocess
import os
import pytest
from pytest import raises
import git2jss.vcs as vcs
import git2jss.exceptions as exceptions

TEST_REPO = 'https://github.com/gkluoe/git2jss-test.git'


@pytest.fixture(scope="session", name="gitrepo")
def fixture_gitrepo(tmpdir_factory):
    """ Return a valid GitRepo object """
    tmp_dir = str(tmpdir_factory.mktemp('gitrepo'))
    _build_local_repo(tmp_dir, remote=TEST_REPO)
    return vcs.GitRepo(tag='test-1.0.0',
                       sourcedir=tmp_dir)


@pytest.fixture(scope="session", name="gitrepo_master")
def fixture_gitrepo_master(tmpdir_factory):
    """ Return a valid GitRepo object """
    tmp_dir = str(tmpdir_factory.mktemp('gitrepo'))
    _build_local_repo(tmp_dir, remote=TEST_REPO)
    return vcs.GitRepo(branch='master',
                       sourcedir=tmp_dir)

@pytest.fixture(scope="session", name="gitrepo_branch001")
def fixture_gitrepo_branch001(tmpdir_factory):
    """ Return a valid GitRepo object """
    tmp_dir = str(tmpdir_factory.mktemp('gitrepo'))
    _build_local_repo(tmp_dir, remote=TEST_REPO)
    return vcs.GitRepo(branch='branch001',
                       sourcedir=tmp_dir)


def _build_local_repo(test_dir, remote=None):
    """ Build a fresh local git repo.
    if `remote` is specified, add the URL
    to the repo as a new git remote
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
        vcs.GitRepo(tag='NotATag',
                    sourcedir=str(tmpdir))


def test_new_no_remote(tmpdir):
    """ Directory has no git remotes configured """
    _build_local_repo(str(tmpdir))
    with raises(vcs.NoRemoteError):
        vcs.GitRepo(tag='NotATag',
                    sourcedir=str(tmpdir))


def test_too_many_remotes(tmpdir):
    """ Directory has too many remotes configured """
    _build_local_repo(str(tmpdir),
                      remote=TEST_REPO)
    # Add another remote
    subprocess.call(["git", "remote",
                     "add", "notherone",
                     "https://notarepo.example.com"],
                    cwd=str(tmpdir))

    with raises(vcs.TooManyRemotesError):
        vcs.GitRepo(tag='NotATag',
                    sourcedir=str(tmpdir))


def test_new_no_tag_on_remote(tmpdir):
    """ Remote doesn't have our tag """
    _build_local_repo(str(tmpdir),
                      remote=TEST_REPO)
    with raises(vcs.RefNotFoundError):
        vcs.GitRepo(tag='NotATag',
                    sourcedir=str(tmpdir))

def test_new_no_branch_on_remote(tmpdir):
    """ Remote doesn't have our tag """
    _build_local_repo(str(tmpdir),
                      remote=TEST_REPO)
    with raises(vcs.RefNotFoundError):
        vcs.GitRepo(branch='NotBranch',
                    sourcedir=str(tmpdir))

def test_new_with_tag(gitrepo):
    """ Successfully instantiate a GitRepo """
    # '.git' should have been trimmed from the repo URL
    assert gitrepo.remote_url == TEST_REPO[:-4]
    assert gitrepo.remote_name == "origin"
    assert gitrepo.tag == "test-1.0.0"


def test_new_with_master(gitrepo_master):
    """ Successfully instantiate a GitRepo """
    # '.git' should have been trimmed from the repo URL
    assert gitrepo_master.remote_url == TEST_REPO[:-4]
    assert gitrepo_master.remote_name == "origin"
    assert gitrepo_master.branch == "master"


def test_new_with_branch001(gitrepo_branch001):
    """ Successfully instantiate a GitRepo """
    # '.git' should have been trimmed from the repo URL
    assert gitrepo_branch001.remote_url == TEST_REPO[:-4]
    assert gitrepo_branch001.remote_name == "origin"
    assert gitrepo_branch001.branch == "branch001"



def test_check_path_to_file(gitrepo):
    """ Can we return the path to a file? """
    assert (gitrepo.path_to_file("README.md") ==
            os.path.join(gitrepo.tmp_dir, 'README.md'))

    # Paths should come back as absolute paths
    assert (gitrepo.path_to_file("././././././README.md") ==
            os.path.join(gitrepo.tmp_dir, 'README.md'))
    assert (gitrepo.path_to_file("././foo/../././././README.md") ==
            os.path.join(gitrepo.tmp_dir, 'README.md'))

    # And of course the file should exist!
    assert os.path.isfile(os.path.join(gitrepo.tmp_dir,
                                       'README.md'))


def test_check_non_file_ascii(gitrepo):
    """ Check a non-existing file with an ascii name """
    with raises(vcs.FileNotFoundError):
        assert gitrepo.path_to_file(u"kf/dsd/fsd/fs/sd.blah")


@pytest.mark.xfail  # We don't seem to support unicode filenames
def test_check_non_file_unicode(gitrepo):
    """ Check a non-existing file with a unicode name """
    with raises(vcs.FileNotFoundError):
        assert gitrepo.path_to_file(u"kf/dsd/⌨fsd/⌨fs/sd.blah")


# def test_check_create_tag(gitrepo):
#     """ Check we can create a new tag """
#     # We've already got a nice random string
#     newtag = os.path.basename(gitrepo.tmp_dir)
#     # Poke a new tag
#     oldtag = gitrepo.tag
#     try:
#         gitrepo.tag = newtag
#         assert not gitrepo._has_ref_on_remote(newtag)
#         gitrepo.create_tag(msg="Tagged by pytest")
#         assert gitrepo._has_tag_on_remote(newtag)
#     finally:
#         gitrepo.tag = oldtag


def test_get_file_info(gitrepo):
    """ Test getting the git info for a known file """
    filename = 'README.md'
    info = {'ORIGIN': 'https://github.com/gkluoe/git2jss-test',
            'PATH': '{}'.format(filename),
            'DATE': '"Sat Mar 17 09:14:38 2018 +0000"',
            'VERSION': 'test-1.0.0',
            'LOG': '371a104 - Sat, 17 Mar 2018 09:14:38 +0000 noreply@github.com: \n Initial commit'}
    assert gitrepo.file_info(filename) == info

def test_get_file_info_branch(gitrepo_branch001):
    """ Test getting the git info for a known file """
    filename = 'README.md'
    info = {'ORIGIN': 'https://github.com/gkluoe/git2jss-test',
            'PATH': '{}'.format(filename),
            'DATE': '"Fri Apr 5 08:54:43 2019 +0100"',
            'VERSION': 'd63e87d0e695e3304d2f2a8137b1da9d88587bf4 on branch: branch001',
            'LOG': ('d63e87d - Fri, 5 Apr 2019 08:54:43 +0100 g.lee@ed.ac.uk: \n Add a test branch\n\n'
                    '371a104 - Sat, 17 Mar 2018 09:14:38 +0000 noreply@github.com: \n Initial commit')}
    assert gitrepo_branch001.file_info(filename) == info

def test_get_file_info_notexist(gitrepo):
    """ Get info for a non-existing file """
    filename = 'lsh/fsd/f/s/avads/fa/'
    with raises(vcs.FileNotFoundError):
        gitrepo.file_info(filename)


def test_get_file(gitrepo):
    """ Test getting an open handle to a file """
    import io
    filename = 'README.md'
    handle = gitrepo.get_file(filename)

    assert isinstance(handle, io.TextIOWrapper)
    assert handle.read() == (u'# git2jss-test\nThis exists purely to test '
                             'https://github.com/gkluoe/git2jss\n')


def test_error_during_checkout(gitrepo, tmpdir_factory):
    """ Provoke a failure during checkout """
    gitrepo.remote_url = 'https://www.example.com/blah'
    gitrepo.tmp_dir = str(tmpdir_factory.mktemp('checkout_error'))
    with raises(exceptions.Git2JSSError,
                match=".*repository 'https://www.example.com/blah.git/' not found"):
        gitrepo._clone_to_tmp()
