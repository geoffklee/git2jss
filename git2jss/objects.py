""" Various objects that we might sync with the JSS """
from __future__ import absolute_import, print_function
from base64 import b64encode
from string import Template
import jss
import git2jss


class TargetNotFoundError(BaseException):
    """ Target wasn't found """
    pass


class JSSObject(object):
    """ Generic Object """

    vcs = None
    jss = None

    source_name = None
    source_file = None
    target_name = None
    target_object = None


    def __init__(self, repo, _jss, source_file, target=None, target_type='Script'):
        """ Load source file from the vcs and
        target object from the JSS

        `repo` should be a repo from the vcs module
        `jss` should be a JSS object
        `source_file` should be the name of the source file
        """

        self.source_name = source_file
        self.target_name = target or source_file
        self.target_type = target_type
        self.repo = repo
        self._jss = _jss

        self._load_target_object()
        self._load_source_file()


    def _load_target_object(self):
        """ Load the target pbject from the JSS
        """
        try:
            # Calls _jss.'target_type'(): eg _jss.Script()
            jss_method = getattr(self._jss, self.target_type)
            self.target_object = jss_method(self.target_name)
        except jss.JSSGetError as err:
            if err.message.find('404'):
                raise
                #raise TargetNotFoundError(
                #    "Couldn't find target {} of type {} on the JSS"
                #    .format(self.target_name, self.target_type))
            else:
                raise
        else:
            print("Loaded {} from the JSS".format(self.target_name))


    def _load_source_file(self):
        """ Load the source file from the VCS
        """
        try:
            self.source_file = self.repo.get_file(self.source_name)
        except:
            raise
        else:
            print ("Loaded {} from version control".format(self.source_name))



    def update(self, should_template):
        """ Stub method which should be overriden for
        different types of object which subclass this one
        """
        pass


    def save(self):
        """ Write the object back to the JSS
        """
        try:
            self.target_object.save()
        except:
            raise
        else:
            print("Saved {} to the jss".format(self.target_name))




class JSSScript(JSSObject):
    """ A Script """

    OBJECT_TYPE = "Script"

    def __init__(self, *args, **kwargs):
        kwargs['target_type'] = self.OBJECT_TYPE
        super(JSSScript, self).__init__(*args, **kwargs)


    def update(self, should_template=True):
        """ Update the notes field to contain the git log,
            and, if requested, template the script
        """

        script_info = self.repo.file_info(self.source_name)

        # Add log to the notes field
        self.target_object.find('notes').text = script_info['LOG']

        # Update the script - we need to write a base64 encoded version
        # of the contents of source_file into the 'script_contents_encoded'
        # element of the script object
        if should_template:
            print("Templating file...")
            self.target_object.find('script_contents_encoded').text = b64encode(
                template_file(self.source_file, script_info).encode('utf-8'))
        else:
            print("No templating requested.")
            self.target_object.find('script_contents_encoded').text = b64encode(
                self.source_file.read().encode('utf-8'))

        # Only one of script_contents and script_contents_encoded should be sent
        # so delete the one we are not using.
        self.target_object.remove(self.target_object.find('script_contents'))



class JSSComputerExtensionAttribute(JSSObject):
    """ A ComputerExtensionAttribute """

    OBJECT_TYPE = "ComputerExtensionAttribute"

    def __init__(self, *args, **kwargs):
        kwargs['target_type'] = self.OBJECT_TYPE
        super(JSSComputerExtensionAttribute, self).__init__(*args, **kwargs)





def template_file(handle, script_info):
    """ Template a file. Pass in an open
        file handle and receive a string containing
        the templated text. We use a custom delimiter to
        reduce the risk of collisions
    """

    class JSSTemplate(Template):
        """ Template subclass with a custom delimiter """
        delimiter = '@@'

    text = handle.read()
    tmpl = JSSTemplate(text)
    out = None
    try:
        out = tmpl.safe_substitute(script_info)
    except:
        print("Failed to template this script.")
        raise

    return out
