.. image:: https://dev.azure.com/gklee/git2jss/_apis/build/status/gkluoe.git2jss?branchName=master

Git2JSS
===============================

Version : v2.0.0

Author: Geoff Lee

Overview
--------
**Question:** *How do you ensure that all changes to Scripts and ComputerExtensionAttributes in your JAMF JSS are logged, reversible, and match what you have in source control?*

**Answer:** *Make it zero-effort.*

Using *Git2jss*, after making changes to JSS Scripts or CEAs in your dev/test environment and pushing them to a Git repository, you can export a tagged copy to your JSS, complete with the Git changelog in the 'Notes' field. Reverting a change is as easy as exporting the previous tagged version.

You can also use this script in a Continuous Integration pipeline to export scripts from the head of a given branch to your JSS.

Templating of some important values is also supported, so your scripts automatically contain details of the last change, and where they can be found in source control.

Passwords are stored in the system keychain by default.

Installation / Usage
--------------------

NB: the ``python-jss`` and ``keyring`` modules are required. If manually installing, you'll need to make sure they are present. 
Installing via pip should take care of this for you.

Install via pip
```````````````

If you're installing into a virtualenv

    ``$ pip install git2jss``

should be all you need to do.
    

If installing onto OS X 10.13 and not using a virtualenv,
you'll need to use sudo, and install a missing dependency:

    ``$ sudo pip install git2jss``
    
    ``$ sudo pip install cryptography``

Or manually
````````````

Clone the repo and run the setup script

    ``$ git clone https://github.com/gkluoe/git2jss.git``

    ``$ python setup.py install``
    


Examples
--------

Commandline
```````````

You can use it on the commandine like this::

  # Export the file localscript.sh to a Script object on the JSS called do_something_great.sh
  # using the existing tag v0.0.9
  
  $ git tag v0.0.9 && git push origin v0.0.9
  $ git2jss --file localscript.sh --name do_something_great.sh --tag v0.0.9
  
  # Export the file run-softwareupdate.py at the head of the master branch
  # to an object on the JSS with the same name
  
  $ git2jss --file run-softwareupdate.py --branch master

  # Export the file check_firewall.sh to a ComputerExtensionAttribute object on the JSS called 
  # FirewallCheck, using the existing tag v0.0.9
  
  $ git2jss --mode ComputerExtensionAttribute --file check_firewall.sh --name check-firewall --tag v0.0.9

  # Export each script in the current folder that has a script object on the server
  # with a matching name, and exists at tag v1.0.2
  
  $ git2jss --all --tag v1.0.2
  
  # Or do the same for all files at the head of branch 'production'
  
  $ git2jss --all --branch production

  # Show information about the currently configured JSS (or enter details if none configured)
  
  $ git2jss --jss-info

Templating
``````````

The following variables, if embedded into your script, will be replaced with the indicated values when being transferred to the JSS

+--------------+-------------------------------------------------------------------------------------------------+
| Variable     | Value                                                                                           | 
+==============+=================================================================================================+
| ``@@VERSION``| If --tag was used: The name of the git tag that you have specified (eg v1.0.1)                  |
|              | If --branch was used: The commit hash of the last change of the file, and a note of the branch  |
+--------------+-------------------------------------------------------------------------------------------------+
| ``@@ORIGIN`` | Assuming you have a git remote called 'origin', the URL thereof                                 |
|              | (eg https://github.com/uoe-macos/jss)                                                           |
+--------------+-------------------------------------------------------------------------------------------------+
| ``@@PATH``   | The name of the file in the git repository identified by @@ORIGIN``                             |
+--------------+-------------------------------------------------------------------------------------------------+
| ``@@DATE``   | The date of the *last change* of the file in Git                                                |
+--------------+-------------------------------------------------------------------------------------------------+
| ``@@USER``   | The username used by git2jss to authenticate to the JSS at                                      |
|              | the time the script was exported                                                                |
+--------------+-------------------------------------------------------------------------------------------------+
| ``@@LOG``    | The entire Git log for this script, formatted thus:                                             |
|              | ``'%h - %cD %ce: %n %s%n'``                                                                     |
+--------------+-------------------------------------------------------------------------------------------------+

``@@LOG`` is used to construct the 'Notes' field in the JSS, overwriting anything that was present previously.


Contributing
------------

Issues and pull requests are very welcome!
