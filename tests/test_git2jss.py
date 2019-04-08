# --*-- encoding: utf-8 --*--
""" General tess """
from __future__ import print_function
import plistlib
import tempfile
import os
import getpass
from collections import deque
import pytest
from pytest import raises

import jss
import git2jss.jss_keyring
import mock
from mock import patch

# This is brain-melting. See:
# https://stackoverflow.com/questions/18011902/py-test-pass-a-parameter-to-a-fixture-function
# and
# https://docs.pytest.org/en/latest/fixture.html
#
# The idea here is that this fixture returns a function which takes an optional argument
# containing the data that we want in our test preferences file.


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


def _check_prefs_values(prefs_file_no_keychain, prefs_data):
    """ Check that the values in a JSSPrefs object instantiated
    using the file `test_prefs` match the values in `prefs_data`
    """
    jss_prefs = jss.JSSPrefs(preferences_file=prefs_file_no_keychain)

    assert jss_prefs.user == prefs_data.get('jss_user')
    assert jss_prefs.url == prefs_data.get('jss_url')
    assert jss_prefs.password == prefs_data.get('jss_pass')


def test_get_prefs_unicode(prefs_file_no_keychain):
    """ Can we get our prefs? Can they handle unicode? """
    prefs_data = {"jss_url": u"https://some.domain.example.com/directory:port",
                  "jss_user": u"ਫ ਬ ਭ 1 2 3",
                  "jss_pass": u"զ է ը թ 4 5 6"}

    _check_prefs_values(prefs_file_no_keychain(
        prefs_data=prefs_data), prefs_data)


def test_get_prefs_ascii(prefs_file_no_keychain):
    """ Can we get our prefs? Can they handle unicode? """
    prefs_data = {"jss_url": u"https://some.domain.example.com/directory:port",
                  "jss_user": u"slartibartfarst",
                  "jss_pass": u"123blah456blah"}

    _check_prefs_values(prefs_file_no_keychain(
        prefs_data=prefs_data), prefs_data)


def test_jss_info_no_keychain(prefs_file_no_keychain, capsys):
    """ Test displaying JSS info when we are not using the
    system keychain
    """
    args = ["--jss-info", "--no-keychain"]
    with pytest.raises(SystemExit):
        git2jss.main(argv=args, prefs_file=prefs_file_no_keychain())
        out = capsys.readouterr()[0]
        assert out.find(
            """JSS: https://some.domain.example.com/directory:port\nUsername: slartibartfarst""")


def test_prefs_setup(capsys, monkeypatch):
    from functools import partial
    import getpass
    import requests

    def _make_multiple_inputs(inputs):
        """ provides a function to call for every input requested. """
        def next_input(_):
            """ provides the first item in the list. """
            return inputs.popleft()
        return next_input

    prefs_values = {"jss_url": u"https://git2jss.test.example.com/url:9999",
                    "jss_user": u"liasufgoadsvbousyvboads8yvoasduvhybouvybasdouvybas",
                    "jss_pass": u"ufygasiufygasdoufygasoufygaoduygasdoufyasdgouasydgfoa"}

    # Patch the builtin raw_input, and the getpass.getpass funtcion to return
    # some values that we would expect a user to type.
    monkeypatch.setitem(__builtins__, 'raw_input', _make_multiple_inputs(
        deque([prefs_values['jss_url'], prefs_values['jss_user'], "N", "N", "N", "N", "N", "N", "N"])))

    monkeypatch.setattr('getpass.getpass', lambda x: prefs_values['jss_pass'])

    # The _get_user_input() function's default value has already mapped a variable to
    # the unmodified version of raw_input, so we need to reload it at this point to give
    # the function access to our patched version.
    reload(jss.jss_prefs)

    # We don't care about the underlying module's handling of distribution servers
    # and patching out this function avoids us attemoting to connect to the JSS.
    monkeypatch.setattr('jss.jss_prefs._handle_dist_server', lambda x, y: "")

    # We also don't care about repositories
    monkeypatch.setattr(
        'git2jss.jss_keyring.KJSSPrefs._handle_repos', lambda x, y: "")

    # Now we can do stuff. Test that the preferences creation routine stores the
    # credentials and cam retrieve them from its prefs file.
    prefs_file = tempfile.mktemp()
    with pytest.raises(SystemExit):
        git2jss.main(argv=['--jss-info'], prefs_file=prefs_file)

    out = capsys.readouterr()[0]
    assert out.find("JSS: {}".format(prefs_values['jss_url'])) 
    assert out.find("Username: {}".format(prefs_values['jss_url'])) 
    assert out.find("File: {}".format(prefs_file)) 

    # The password should have been stored in the system keychain:
    keychain_password = git2jss.jss_keyring.get_creds_from_keychain(prefs_values['jss_url'],
                                                                    prefs_values['jss_user'])

    assert(keychain_password == prefs_values['jss_pass'])

    os.unlink(prefs_file)


def test_create_script_from_custom_src_branch():
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", os.path.join(os.getcwd(), "_jss"), 
            "--name", "macad-2018-test.py",
            "--branch", "master"]
    git2jss.main(argv=args)
    # TODO: check that the created script is what we expect


def test_create_script_from_dot_branch():
    cwd = os.getcwd()
    try:
        os.chdir('_jss')
        args = ["--mode", "Script", 
                "--file", "coreconfig-softwareupdate-run.py",
                "--name", "macad-2018-test.py",
                "--branch", "master"]
        git2jss.main(argv=args)
    finally:
        os.chdir(cwd)
    # TODO: check that the created script is what we expect

def test_create_script_from_custom_src_tag():
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", os.path.join(os.getcwd(), "_jss"), 
            "--name", "macad-2018-test.py",
            "--tag", "0.0.49"]
    git2jss.main(argv=args)
    # TODO: check that the created script is what we expect


def test_create_script_from_dot_tag():
    cwd = os.getcwd()
    try:
        os.chdir('_jss')
        args = ["--mode", "Script", 
                "--file", "coreconfig-softwareupdate-run.py",
                "--name", "macad-2018-test.py",
                "--tag", "0.0.49"]
        git2jss.main(argv=args)
    finally:
        os.chdir(cwd)
    # TODO: check that the created script is what we expect

def test_exception_invalid_tag():
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", os.path.join(os.getcwd(), "_jss"), 
            "--name", "macad-2018-test.py",
            "--tag", "notatag"]
    with raises(git2jss.vcs.RefNotFoundError):
        git2jss.main(argv=args)
    
def test_exception_invalid_branch():
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", os.path.join(os.getcwd(), "_jss"), 
            "--name", "macad-2018-test.py",
            "--branch", "notabranch"]
    with raises(git2jss.vcs.RefNotFoundError):
        git2jss.main(argv=args)

def test_exception_invalid_target():
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", os.path.join(os.getcwd(), "_jss"), 
            "--name", "NotAJSSObject",
            "--tag", "0.0.49"]
    with raises(git2jss.processors.TargetNotFoundError):
        git2jss.main(argv=args)

def test_exception_invalid_repo():
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", "/tmp", 
            "--name", "macad-2018-test.py",
            "--tag", "0.0.49"]
    with raises(git2jss.vcs.NotAGitRepoError):
        git2jss.main(argv=args)


def test_exception_invalid_file():
    args = ["--mode", "Script", 
            "--file", "NotAFile",
            "--local-repo", "_jss", 
            "--name", "macad-2018-test.py",
            "--tag", "0.0.49"]
    with raises(git2jss.vcs.FileNotFoundError):
        git2jss.main(argv=args)


def test_exception_invalid_mode(capsys):
    args = ["--mode", "NotAMode", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", "_jss", 
            "--name", "macad-2018-test.py",
            "--tag", "0.0.49"]
    with pytest.raises(SystemExit):
        git2jss.main(argv=args)
    out = capsys.readouterr()[0]
    assert out.find(
        """(choose from 'Script', 'ComputerExtensionAttribute')""")


def test_exception_no_tag_or_branch(capsys):
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", "_jss", 
            "--name", "macad-2018-test.py",
            ]
    with pytest.raises(SystemExit):
        git2jss.main(argv=args)
    out = capsys.readouterr()[0]
    assert out.find(
        """(Please specify with '--tag' or '--branch')""")