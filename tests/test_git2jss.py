# --*-- encoding: utf-8 --*--
""" General tess """
from __future__ import print_function
import plistlib
import tempfile
import os

import jss
import git2jss

import pytest

# This is brain-melting. See:
# https://stackoverflow.com/questions/18011902/py-test-pass-a-parameter-to-a-fixture-function
# and
# https://docs.pytest.org/en/latest/fixture.html
#
# The idea here is that this fixture returns a function which takes an optional argument
# containing the data that we want in our test preferences file.


@pytest.fixture(scope="function")
def test_prefs(request):
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


def _check_prefs_values(test_prefs, prefs_data):
    """ Check that the values in a JSSPrefs object instantiated
    using the file `test_prefs` match the values in `prefs_data`
    """
    jss_prefs = jss.JSSPrefs(preferences_file=test_prefs)

    assert jss_prefs.user == prefs_data.get('jss_user')
    assert jss_prefs.url == prefs_data.get('jss_url')
    assert jss_prefs.password == prefs_data.get('jss_pass')


def test_get_prefs_unicode(test_prefs):
    """ Can we get our prefs? Can they handle unicode? """
    prefs_data = {"jss_url": u"https://some.domain.example.com/directory:port",
                  "jss_user": u"ਫ ਬ ਭ 1 2 3",
                  "jss_pass": u"զ է ը թ 4 5 6"}

    _check_prefs_values(test_prefs(prefs_data=prefs_data), prefs_data)


def test_get_prefs_ascii(test_prefs):
    """ Can we get our prefs? Can they handle unicode? """
    prefs_data = {"jss_url": u"https://some.domain.example.com/directory:port",
                  "jss_user": u"slartibartfarst",
                  "jss_pass": u"123blah456blah"}

    _check_prefs_values(test_prefs(prefs_data=prefs_data), prefs_data)


def test_jss_info_no_keychain(test_prefs, capsys):
    """ Test displaying JSS info when we are not using the
    system keychain
    """
    args = ["--jss-info", "--no-keychain"]
    with pytest.raises(SystemExit):
        git2jss.main(argv=args, prefs_file=test_prefs())
        out = capsys.readouterr()[0]
        assert out.find(
            """JSS: https://some.domain.example.com/directory:port\nUsername: slartibartfarst""")
