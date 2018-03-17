""" Tests for the vcs module """
# --*-- encoding: utf-8 --*--
import subprocess
import os
import pytest
from pytest import raises
import git2jss.vcs as vcs

TEST_REPO = 'https://github.com/gkluoe/git2jss-test.git'


@pytest.fixture(scope="session")
def gitrepo(tmpdir_factory):
    tmp_dir = str(tmpdir_factory.mktemp('gitrepo'))
    _build_local_repo(tmp_dir, remote=TEST_REPO)
    return vcs.GitRepo(tag='test-1.0.0',
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
                     "https://notarepo.example.com"],
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
    assert gitrepo.remote_url == TEST_REPO[:-
                                           4]  # .git should have been trimmed
    assert gitrepo.remote_name == "origin"
    assert gitrepo.tag == "test-1.0.0"


def test_check_path_to_file(gitrepo):
    """ Can we return the path to a file? """
    assert (gitrepo.path_to_file("README.md") ==
            os.path.join(gitrepo.tmp_dir, 'README.md'))

    """ Paths should come back as absolute paths """
    assert (gitrepo.path_to_file("././././././README.md") ==
            os.path.join(gitrepo.tmp_dir, 'README.md'))
    assert (gitrepo.path_to_file("././foo/../././././README.md") ==
            os.path.join(gitrepo.tmp_dir, 'README.md'))

    """ And of course the file should exist! """
    assert os.path.isfile(os.path.join(gitrepo.tmp_dir,
                                       'README.md'))


def test_check_non_existing_file_ascii(gitrepo):
    with raises(vcs.FileNotFoundError):
        assert gitrepo.path_to_file(u"kf/dsd/fsd/fs/sd.blah")


@pytest.mark.xfail  # We don't seem to support unicode filenames
def test_check_non_existing_file_unicode(gitrepo):
    with raises(vcs.FileNotFoundError):
        assert gitrepo.path_to_file(u"kf/dsd/⌨fsd/⌨fs/sd.blah")


def test_check_create_tag(gitrepo):
    """ Check we can create a new tag """
    # We've already got a nice random string
    newtag = os.path.basename(gitrepo.tmp_dir)
    # Poke a new tag
    oldtag = gitrepo.tag
    try:
        gitrepo.tag = newtag
        assert not gitrepo.has_tag_on_remote()
        gitrepo.create_tag(msg="Tagged by pytest")
        assert gitrepo.has_tag_on_remote()
    finally:
        gitrepo.tag = oldtag


def test_get_file_info(gitrepo):
    filename = 'README.md'
    info = {'ORIGIN': 'https://github.com/gkluoe/git2jss-test',
            'PATH': '{}'.format(filename),
            'DATE': '"Sat Mar 17 09:14:38 2018 +0000"',
            'VERSION': 'test-1.0.0',
            'LOG': '371a104 - Sat, 17 Mar 2018 09:14:38 +0000 noreply@github.com: \n Initial commit'}

    assert gitrepo.file_info(filename) == info


def test_get_file_info_notexist(gitrepo):
    filename = 'lsh/fsd/f/s/avads/fa/'
    with raises(vcs.FileNotFoundError):
        gitrepo.file_info(filename)


def test_get_file(gitrepo):
    import io
    filename = 'README.md'
    handle = gitrepo.get_file(filename)

    assert isinstance(handle, io.TextIOWrapper)
    assert handle.read() == u'# git2jss-test\nThis exists purely to test https://github.com/gkluoe/git2jss\n'
