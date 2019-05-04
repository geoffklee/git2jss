import pytest
import tempfile
import plistlib
import subprocess
import os
import jss
import git2jss.vcs as vcs

# This filecontains all of our fixtures


# This is brain-melting. See:
# https://stackoverflow.com/questions/18011902/py-test-pass-a-parameter-to-a-fixture-function
# and
# https://docs.pytest.org/en/latest/fixture.html
#
# The idea here is that this fixture returns a function which takes an optional argument
# containing the data that we want in our test preferences file.

@pytest.fixture(scope='session', name='git2jss_test_repo')
def fixture_git2jss_test_repo():
    return 'https://github.com/gkluoe/git2jss-test.git'



@pytest.fixture(scope="function", name="prefs_file_no_keychain")
def fixture_prefs_file_no_keychain(request):
    """ Return a function which creates a test prefs file
    and cleans up afterwards
    """
    def make_test_prefs(prefs_data=None):
        """ Create a test preferences file and clean up afterwards """
        default_data = {"jss_url": u"https://some.domain.example.com/directory:port",
                        "jss_user": u"slartibartfarst",
                        "jss_pass": u"123blah456blah"}

        prefs_data = prefs_data or default_data
        prefs_file = tempfile.mktemp()
        plistlib.writePlist(prefs_data, prefs_file)

        def fin():
            """ Delete temp file """
            print("Deleting temp prefs file")
            os.unlink(prefs_file)
        request.addfinalizer(fin)

        return prefs_file
    return make_test_prefs

@pytest.fixture(scope="function", name="check_prefs_values")
def fixture_check_prefs_values(prefs_file_no_keychain):
    def _check_prefs_values(prefs_file_no_keychain, prefs_data):
        """ Check that the values in a JSSPrefs object instantiated
        using the file `test_prefs` match the values in `prefs_data`
        """
        jss_prefs = jss.JSSPrefs(preferences_file=prefs_file_no_keychain)

        assert jss_prefs.user == prefs_data.get('jss_user')
        assert jss_prefs.url == prefs_data.get('jss_url')
        assert jss_prefs.password == prefs_data.get('jss_pass')
    return _check_prefs_values


@pytest.fixture(scope="session", name="a_jss")
def fixture_a_jss():
    # You'll need to create this file...
    prefs = jkc.KJSSPrefs(preferences_file='tests/com.github.gkluoe.git2jss.plist')
    JSS = jss.JSS(prefs)
    return JSS

@pytest.fixture(scope="session", name="jss_repo")
def fixture_jss_repo(tmpdir_factory):
    """ Return a valid GitRepo object """
    tmp_dir = str(tmpdir_factory.mktemp('source_gitrepo'))
    subprocess.check_call(['git', 'clone', 'https://github.com/uoe-macos/jss', tmp_dir])
    return tmp_dir


@pytest.fixture(scope='session', name='a_gitrepo')
def fixture_a_gitrepo(jss_repo):
    repo = vcs.GitRepo(tag='0.0.49', sourcedir=jss_repo)
    return repo


@pytest.fixture(scope="session", name="gitrepo")
def fixture_gitrepo(tmpdir_factory, git2jss_test_repo):
    """ Return a valid GitRepo object """
    tmp_dir = str(tmpdir_factory.mktemp('gitrepo'))
    _build_local_repo(tmp_dir, remote=git2jss_test_repo)
    return vcs.GitRepo(tag='test-1.0.0',
                       sourcedir=tmp_dir)


@pytest.fixture(scope="session", name="gitrepo_master")
def fixture_gitrepo_master(tmpdir_factory, git2jss_test_repo):
    """ Return a valid GitRepo object """
    tmp_dir = str(tmpdir_factory.mktemp('gitrepo'))
    _build_local_repo(tmp_dir, remote=git2jss_test_repo)
    return vcs.GitRepo(branch='master',
                       sourcedir=tmp_dir)

@pytest.fixture(scope="session", name="gitrepo_branch001")
def fixture_gitrepo_branch001(tmpdir_factory, git2jss_test_repo):
    """ Return a valid GitRepo object """
    tmp_dir = str(tmpdir_factory.mktemp('gitrepo'))
    _build_local_repo(tmp_dir, remote=git2jss_test_repo)
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
