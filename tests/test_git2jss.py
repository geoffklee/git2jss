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


def test_get_prefs_unicode(prefs_file_no_keychain, check_prefs_values):
    """ Can we get our prefs? Can they handle unicode? """
    prefs_data = {"jss_url": u"https://some.domain.example.com/directory:port",
                  "jss_user": u"ਫ ਬ ਭ 1 2 3",
                  "jss_pass": u"զ է ը թ 4 5 6"}

    check_prefs_values(prefs_file_no_keychain(
        prefs_data=prefs_data), prefs_data)


def test_get_prefs_ascii(prefs_file_no_keychain, check_prefs_values):
    """ Can we get our prefs? Can they handle unicode? """
    prefs_data = {"jss_url": u"https://some.domain.example.com/directory:port",
                  "jss_user": u"slartibartfarst",
                  "jss_pass": u"123blah456blah"}

    check_prefs_values(prefs_file_no_keychain(
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


def test_jss_info_no_keychain_prefs_commandline(capsys, prefs_file_no_keychain):
    args = ["--jss-info", "--no-keychain", "--prefs-file", prefs_file_no_keychain()]
    with pytest.raises(SystemExit):
        git2jss.main(argv=args)
    out = capsys.readouterr()[0]
    assert out.find(
        """JSS: https://some.domain.example.com/directory:port\nUsername: slartibartfarst""")

def test_exception_prefs_commandline_invalid(capsys):
    args = ["--jss-info", "--no-keychain", "--prefs-file", "/etc/passwd"]
    with pytest.raises(git2jss.exceptions.Git2JSSError):
        git2jss.main(argv=args)
    out = capsys.readouterr()[0]
    assert out.find(
        """Preferences file""")

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

@pytest.mark.need_jss
def test_create_script_from_custom_src_branch(jss_repo):
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", jss_repo,  
            "--name", "macad-2018-test.py",
            "--branch", "master"]
    git2jss.main(argv=args)
    # TODO: check that the created script is what we expect

@pytest.mark.need_jss
def test_create_script_from_dot_branch(jss_repo):
    cwd = os.getcwd()
    try:
        os.chdir(jss_repo)
        args = ["--mode", "Script", 
                "--file", "coreconfig-softwareupdate-run.py",
                "--name", "macad-2018-test.py",
                "--branch", "master"]
        git2jss.main(argv=args)
    finally:
        os.chdir(cwd)
    # TODO: check that the created script is what we expect

@pytest.mark.need_jss
def test_create_script_from_custom_src_tag(jss_repo):
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", os.path.join(os.getcwd(), jss_repo), 
            "--name", "macad-2018-test.py",
            "--local-repo", jss_repo,  
            "--tag", "0.0.49"]
    git2jss.main(argv=args)
    # TODO: check that the created script is what we expect

@pytest.mark.need_jss
def test_create_script_from_dot_tag(jss_repo):
    cwd = os.getcwd()
    try:
        os.chdir(jss_repo)
        args = ["--mode", "Script", 
                "--file", "coreconfig-softwareupdate-run.py",
                "--name", "macad-2018-test.py",
                "--tag", "0.0.49"]
        git2jss.main(argv=args)
    finally:
        os.chdir(cwd)
    # TODO: check that the created script is what we expect

def test_exception_invalid_tag(prefs_file_no_keychain, jss_repo):
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", jss_repo,  
            "--name", "macad-2018-test.py",
            "--tag", "notatag",
            "--no-keychain"]
    with raises(git2jss.vcs.RefNotFoundError):
        git2jss.main(argv=args, prefs_file=prefs_file_no_keychain())
    
def test_exception_invalid_branch(prefs_file_no_keychain, jss_repo):
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", jss_repo, 
            "--name", "macad-2018-test.py",
            "--branch", "notabranch",
            "--no-keychain"]
    with raises(git2jss.vcs.RefNotFoundError):
        git2jss.main(argv=args, prefs_file=prefs_file_no_keychain())

@pytest.mark.need_jss
def test_exception_invalid_target(jss_repo):
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", jss_repo, 
            "--name", "NotAJSSObject",
            "--tag", "0.0.49"]
    with raises(git2jss.processors.TargetNotFoundError):
        git2jss.main(argv=args)

def test_exception_invalid_repo(prefs_file_no_keychain):
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", "/tmp", 
            "--name", "macad-2018-test.py",
            "--tag", "0.0.49",
            "--no-keychain"]
    with raises(git2jss.vcs.NotAGitRepoError):
        git2jss.main(argv=args, prefs_file=prefs_file_no_keychain())

@pytest.mark.need_jss
def test_exception_invalid_file(prefs_file_no_keychain, jss_repo):
    args = ["--mode", "Script", 
            "--file", "NotAFile",
            "--local-repo", jss_repo, 
            "--name", "macad-2018-test.py",
            "--tag", "0.0.49",
            "--no-keychain"]
    with raises(git2jss.vcs.FileNotFoundError):
        git2jss.main(argv=args, prefs_file=prefs_file_no_keychain())


def test_exception_invalid_mode(capsys, prefs_file_no_keychain, jss_repo):
    args = ["--mode", "NotAMode", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", jss_repo, 
            "--name", "macad-2018-test.py",
            "--tag", "0.0.49",
            "--no-keychain"]
    with pytest.raises(SystemExit):
        git2jss.main(argv=args, prefs_file=prefs_file_no_keychain())
    out = capsys.readouterr()[0]
    assert out.find(
        """(choose from 'Script', 'ComputerExtensionAttribute')""")


def test_exception_no_tag_or_branch(capsys, prefs_file_no_keychain, jss_repo):
    args = ["--mode", "Script", 
            "--file", "coreconfig-softwareupdate-run.py",
            "--local-repo", jss_repo, 
            "--name", "macad-2018-test.py",
            "--no-keychain"
            ]
    with pytest.raises(SystemExit):
        git2jss.main(argv=args, prefs_file=prefs_file_no_keychain())
    out = capsys.readouterr()[0]
    assert out.find(
        """(Please specify with '--tag' or '--branch')""")

