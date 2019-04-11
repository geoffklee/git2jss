# --*-- encoding: utf-8 --*--
import git2jss.processors as processors
import git2jss.vcs as vcs
import git2jss.jss_keyring as jkc
import subprocess
import pytest
from pytest import raises
import jss

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



@pytest.mark.need_jss
def test_new_generic_object(a_gitrepo, a_jss):
    """ Can we create a new Script object? """
    newobj = processors.JSSObject(
        a_gitrepo, a_jss, 'coreconfig-softwareupdate-run.py', target='macad-2018-test.py')
    assert newobj

@pytest.mark.need_jss
def test_new_script_object(a_gitrepo, a_jss):
    """ Can we create a new Script object? """
    newobj = processors.Script(a_gitrepo, a_jss, source_file='coreconfig-softwareupdate-run.py',
                               target='macad-2018-test.py')
    assert newobj

@pytest.mark.need_jss
def test_new_script_object_badfile(a_gitrepo, a_jss):
    """ Can we create a new Script object? """
    with raises(vcs.FileNotFoundError):
        processors.Script(a_gitrepo, a_jss, source_file='sausages',
                                   target='macad-2018-test.py')

@pytest.mark.need_jss
def test_new_script_object_badtarget(a_gitrepo, a_jss):
    """ Can we create a new Script object? """
    with raises(processors.TargetNotFoundError):
        processors.Script(a_gitrepo, a_jss, source_file='coreconfig-softwareupdate-run.py',
                                   target='foo')

@pytest.mark.need_jss
def test_new_cea_object(a_gitrepo, a_jss):
    """ Can we create a new Script object? """
    newobj = processors.ComputerExtensionAttribute(
        a_gitrepo, a_jss, source_file='coreconfig-softwareupdate-run.py', target='test-1')                                                   
    assert newobj

@pytest.mark.need_jss
def test_update_cea_object(a_gitrepo, a_jss):
    """ Can we update a CEA object ? """
    newobj = processors.ComputerExtensionAttribute(
        a_gitrepo, a_jss, source_file='coreconfig-softwareupdate-run.py', target='test-1')                                                   
    
    newobj.update()

@pytest.mark.need_jss
def test_save_cea_object(a_gitrepo, a_jss):
    """ Can we save a CEA object ? """
    newobj = processors.ComputerExtensionAttribute(
        a_gitrepo, a_jss, source_file='coreconfig-softwareupdate-run.py', target='test-1')                                                   
    
    newobj.update()
    newobj.save()


def test_templating(tmpdir):
    """ Does templating work? """
    data = {'a': 'ThisIsA', 'b': 'ThisIsB', 'c': 123}

    handle = tmpdir.mkdir("template").join("test.txt")

    handle.write("@@a - @@b - @@c - @@d")

    out = processors.template_file(handle, data, d=u' గ ఘ ఙ చ ఛ జ ఝ ఞ ట ఠ')

    assert out == u'ThisIsA - ThisIsB - 123 -  గ ఘ ఙ చ ఛ జ ఝ ఞ ట ఠ'
    
