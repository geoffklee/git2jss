import git2jss.vcs as vcs
import tempfile
import pytest
import subprocess
import os


def test_new_gitrepo_not_a_repo():
    tmpdir = tempfile.mkdtemp()
    with pytest.raises(vcs.NotAGitRepoError):
        repo = vcs.GitRepo(tag='0.1.1',
                           sourcedir=tmpdir)
    

def test_new_no_remote():
    tmpdir = tempfile.mkdtemp()
    subprocess.call(["git", "init", "."],
                    cwd=tmpdir)
    with pytest.raises(vcs.NoRemoteError):
        repo = vcs.GitRepo(tag='0.1.1',
                           sourcedir=tmpdir)
    