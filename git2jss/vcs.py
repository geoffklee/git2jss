""" Model for interacting with VCSs """
import subprocess
import tempfile
import shutil
import re
import os


class Git2JSSError(BaseException):
    """ Base git2jss exception """
    pass
    
class TagNotFoundError(Git2JSSError):
    """ Tag wasn't found """
    pass

class TooManyRemotesError(Git2JSSError):
    """ We can only handle one remote """
    pass

class NoRemoteError(Git2JSSError):
    """ There needs to be at least one remote """

class FileNotFoundError(Git2JSSError):
    """ File Not Found """
    pass

class GitRepo():
    """ Provides helper methods to interact with Git """

    def __init__(self, tag, create=False):
        """ Create a GitRepo object which represents the 
        repository at state `tag` 
        """

        self.tag = tag
        self.remote_name = self._find_remote_name()
        self.remote_url = self._find_remote_url()

        self.TMPDIR = tempfile.mkdtemp()

        if self.tag_exists_on_remote():
            self._clone_to_tmp()
            
        else:
            if not create:
                raise TagNotFoundError("tag doesn't exist on git remote: {}"
                                       .format(self.tag))
            else:
                self.create_tag()
                self.__init__(tag) #pylint: disable=non-parent-init-called

                
    def __del__(self):
        """ Called when there are 0 references left to this 
        object 
        """
        # I don't think this is the best way to do this.
        # we should be using a context manager but I don't know
        # how to make that work in this situation
        
        # Clean up our temp dir
        if os.path.exists(self.TMPDIR):
            print("Cleaning up tmpdir {}".format(self.TMPDIR))
            shutil.rmtree(self.TMPDIR)

        
    def _find_remote_name(self):
        """ Set the name of the current git remote.
        Repositories with more than 1 remote are not 
        currently supported.
        """
        remotes = subprocess.check_output(['git', 'remote']).strip().split('\n')

        if len(remotes) > 1:
            raise TooManyRemotesError("Don't know how to handle more than 1 remote: {}".format(remotes))
        elif len(remotes) < 1:
            raise NoRemoteError("No Git remote is configured")

        return remotes[0]                 

    
    def _find_remote_url(self):
        """ Divine the URL of our git remote, using the 
        name in self.remote_name
        """
        print("Remote: {}".format(self.remote_name))

        _url = subprocess.check_output(["git", "config", "--get",
                                        "remote." + self.remote_name +
                                        ".url"]).strip()
        # Normalise URL to not end with '.git'
        if re.search(r'\.git$', _url):
            _url = _url[:-4]

        return _url          

    
    def _clone_to_tmp(self):
        """ Check out a fresh copy of the `tag` we are going to operate on
            script_tag must be present on the git master
        """
        try:
            print("git remote: {}").format(self.remote_url)
            fnull = open(os.devnull, 'w')
            subprocess.check_call(["git", "clone", "-q", "--branch",
                                   self.tag, self.remote_url + ".git", self.TMPDIR],
                                  stderr=subprocess.STDOUT,
                                  stdout=fnull)
        except subprocess.CalledProcessError:
            raise Git2JSSError("Couldn't check out tag %s: are you sure it exists?" % self.tag)
        else:
            return True
        

    def create_tag(self, msg='Tagged by Git2jss'):
        """ Create tag and push to git remote """
        subprocess.check_call(['git', 'tag', '-a', self.tag, '-m', msg])
        # subprocess.check_call(['git', 'push', 'origin', self.tag])
        print("Tag {} pushed to got remote".format(self.tag))

        
    def file_info(self, filename):
        """ Load information about ourself """
        if self.path_to_file(filename):
            git_info = {}
            git_info['VERSION'] = self.tag
            git_info['ORIGIN'] = self.remote_url
            git_info['PATH'] = filename
            git_info['DATE'] = subprocess.check_output(["git", "log",
                                                        "-1", '--format="%ad"',
                                                        filename], cwd=self.TMPDIR).strip()
            # git_info['USER'] = jss_prefs.user
            git_info['LOG'] = subprocess.check_output(["git", "log",
                                                       '--format=%h - %cD %ce: %n %s%n',
                                                       filename], cwd=self.TMPDIR).strip()
            return git_info

    def path_to_file(self, filename):
        """ Return absolute path to `filename` inside
        our temporary directory
        """
        path = os.path.join(self.TMPDIR, filename)
        if os.path.exists(path):
            return path
        else:
            raise FileNotFoundError("Couldn't find file {} at tag {}"
                                          .format(filename, self.tag))

        
    def tag_exists_on_remote(self):
        """ Check whether `tag` exists in the current repo
        return True or false.
        """
        # Get tags from the git remote
        taglist = subprocess.check_output(['git', 'ls-remote', '--tags'])

        # Parse into a list of tags that exist on the git remote
        tags = [t.split('/')[-1:][0] for t in taglist.split('\n')]

        # Does tag exist?
        return self.tag in tags
