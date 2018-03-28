# --*-- encoding: utf-8 --*--
import git2jss.processors as processors
import git2jss.vcs as vcs
import git2jss.jss_keyring as jkc
import pytest
from pytest import raises
import jss

# You'll need to create this file...
prefs = jkc.KJSSPrefs(preferences_file='tests/com.github.gkluoe.git2jss.plist')

JSS = jss.JSS(prefs)
repo = vcs.GitRepo(tag='0.0.49', sourcedir='_JSS')

def test_new_generic_object():
    """ Can we create a new Script object? """
    newobj = processors.JSSObject(
        repo, JSS, 'coreconfig-softwareupdate-run.py', target='macad-2018-test.py')
    assert newobj


def test_new_script_object():
    """ Can we create a new Script object? """
    newobj = processors.Script(repo, JSS, source_file='coreconfig-softwareupdate-run.py',
                               target='macad-2018-test.py')
    assert newobj


def test_new_script_object_badfile():
    """ Can we create a new Script object? """
    with raises(vcs.FileNotFoundError):
        processors.Script(repo, JSS, source_file='sausages',
                                   target='macad-2018-test.py')


def test_new_script_object_badtarget():
    """ Can we create a new Script object? """
    with raises(processors.TargetNotFoundError):
        processors.Script(repo, JSS, source_file='coreconfig-softwareupdate-run.py',
                                   target='foo')


def test_new_cea_object():
    """ Can we create a new Script object? """
    newobj = processors.ComputerExtensionAttribute(
        repo, JSS, source_file='coreconfig-softwareupdate-run.py', target='test-1')                                                   
    assert newobj


def test_update_cea_object():
    """ Can we update a CEA object ? """
    newobj = processors.ComputerExtensionAttribute(
        repo, JSS, source_file='coreconfig-softwareupdate-run.py', target='test-1')                                                   
    
    newobj.update()


def test_save_cea_object():
    """ Can we save a CEA object ? """
    newobj = processors.ComputerExtensionAttribute(
        repo, JSS, source_file='coreconfig-softwareupdate-run.py', target='test-1')                                                   
    
    newobj.update()
    newobj.save()


def test_templating(tmpdir):
    """ Does templating work? """
    data = {'a': 'ThisIsA', 'b': 'ThisIsB', 'c': 123}

    handle = tmpdir.mkdir("template").join("test.txt")

    handle.write("@@a - @@b - @@c - @@d")

    out = processors.template_file(handle, data, d=u' గ ఘ ఙ చ ఛ జ ఝ ఞ ట ఠ')

    assert out == u'ThisIsA - ThisIsB - 123 -  గ ఘ ఙ చ ఛ జ ఝ ఞ ట ఠ'
    
