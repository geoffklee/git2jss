import jss
import getpass
import keyring
import os
import readline   # pylint: disable=unused-import
import subprocess
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

from jss.exceptions import (JSSError, JSSPrefsMissingKeyError)

from jss.tools import (is_osx, loop_until_valid_response)
try:
    from jss.contrib import FoundationPlist
except ImportError as err:
    # If using OSX, FoundationPlist will need Foundation/PyObjC
    # available, or it won't import.

    if is_osx():
        print "Warning: Import of FoundationPlist failed:", err
        print "See README for information on this issue."
    import plistlib

class KJSSPrefs(jss.JSSPrefs):
    """ This is a subclass of the JSSPrefs class which stores passwords in 
        the system keychain, rather than in plaintext in a preference file.
    """
    
    def configure(self):
        """Prompt user for config and write to plist

        Uses preferences_file argument from JSSPrefs.__init__ as path
        to write.
        """
        _get_user_input = jss.jss_prefs._get_user_input # pylint: disable=protected-access 
        root = ElementTree.Element("dict")
        print ("It seems like you do not have a preferences file configured. "
               "Please answer the following questions to generate a plist at "
               "%s for use with python-jss." % self.preferences_file)

        self.url = jss.jss_prefs._get_user_input(  # pylint: disable=protected-access 
            "The complete URL to your JSS, with port (e.g. "
            "'https://mycasperserver.org:8443')\nURL: ", "jss_url", root)

        self.user = _get_user_input("API Username: ", "jss_user", root)

        self.password = getpass.getpass("API User's Password: ")

        store_creds_in_keychain(self.url, self.user, self.password)

        print ("Password for jss %s has been stored"
               "in the system keychain") % self.url

        verify_prompt = ("Do you want to verify that traffic is encrypted by "
                         "a certificate that you trust?: (Y|N) ")
        self.verify = _get_user_input(verify_prompt, "verify", root,
                                      loop_until_valid_response)

        self._handle_repos(root)

        self._write_plist(root)
        print "Preferences created.\n"

    def parse_plist(self, preferences_file):
        """Try to reset preferences from preference_file."""
        preferences_file = os.path.expanduser(preferences_file)

        # Try to open using FoundationPlist. If it's not available,
        # fall back to plistlib and hope it's not binary encoded.
        try:
            prefs = FoundationPlist.readPlist(preferences_file)
        except NameError:
            try:
                prefs = plistlib.readPlist(preferences_file)
            except ExpatError:
                # If we're on OSX, try to convert using another
                # tool.
                if is_osx():
                    subprocess.call(["plutil", "-convert", "xml1",
                                     preferences_file])
                    prefs = plistlib.readPlist(preferences_file)

        self.preferences_file = preferences_file

        self.user = prefs.get("jss_user")
        self.url = prefs.get("jss_url")

        self.plain_password = prefs.get("jss_pass")

        # Previous versions might have left a plaintext password in
        # a preferences file. Offer to move it to the keychain and
        # bail if the user refuses: this is, after all, the 'K'JSSPrefs
        # class.
        if self.url and self.user and self.plain_password:
            answer = None
            question = ("Warning: we found a plaintext password in the "
                        "prefs file, and you didn't specify '--no-keychain'.\n"
                        "git2jss can remove the plaintext password "
                        "from the file and move it to the keychain for you. \n"
                        "This is almost certainly a good idea but be warned "
                        "that the jss-python module is not comptible with "
                        "keychain-stored passwords.\nThat won't cause you a "
                        "problem unless you need to use jss-python on this machine "
                        "in a different context.\n")
            print question

            while answer not in ['y', 'n']:
                answer = raw_input('Do you want to move the password out of the plist file? (y|n)')
                
            if answer is 'y':
                store_creds_in_keychain(self.url, self.user, self.plain_password)
                prefs.pop("jss_pass")
                self.write_plist_from_dict(prefs)
                print "Password moved into keychain"
                
            else:
                print ("OK, on your own head be it.\n"
                       "You can use the --no-keychain flag to continue with "
                       "the plaintext password.")
                raise JSSError("Plaintext password without --no-keychain")
                     
        self.password = get_creds_from_keychain(self.url, self.user)
        
        if not all([self.user, self.password, self.url]):
            raise JSSPrefsMissingKeyError("Some preferences are missing. Please "
                                          "delete %s and try again." % self.preferences_file)

        # Optional file repository array. Defaults to empty list.
        self.repos = []
        for repo in prefs.get("repos", []):
            self.repos.append(dict(repo))

        self.verify = prefs.get("verify", True)
        self.suppress_warnings = prefs.get("suppress_warnings", True)

    def write_plist_from_dict(self, prefs):
        """ Write the plist, using the values in the dict `prefs` """
        root = ElementTree.Element("dict")
        
        for key_name in prefs.keys():
            val = prefs.get(key_name)
            ElementTree.SubElement(root, "key").text = key_name
            if isinstance(val, bool):
                string_val = "true" if val else "false"
                ElementTree.SubElement(root, string_val)
            else:
                ElementTree.SubElement(root, "string").text = val
        self._write_plist(root) # pylint: disable protected-access
                

def store_creds_in_keychain(service, user, pwd):
    """ Attempt to store the JSS credentials in the keychain """
    try:
        keyring.set_password(service, user, pwd)
    except keyring.errors.KeyringError as error:
        print "Failed to store credentials in keychain: {}".format(error)
        print "If you are running in a virtualenv, this is expected"
        print "See: https://github.com/jaraco/keyring/issues/219"
        raise


def get_creds_from_keychain(service, user):
    """" Fetch the credentials for `jss_url` from the keychain """
    try:
        result = keyring.get_password(service, user)
    except keyring.errors.KeyringError as error:
        print "Failed to get credentials from keychain: {}".format(error)
        print "If you are running in a virtualenv, this is expected"
        print "See: https://github.com/jaraco/keyring/issues/219"
        raise
    
    if result:
        return result
    else:
        raise keyring.errors.KeyringError(("Couldn't find a password in the keychain for\n"
                                           "%s on %s"  % (user, service)))
