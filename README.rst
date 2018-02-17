Git2JSS
===============================

version number: 0.0.6

author: Geoff Lee

Overview
--------
**Question:** *How do you ensure that all changes you scripts in your JAMF JSS are logged, reversible, and match what you have in source control?*

**Answer:** *Automate it!*

*Git2jss* allows you to make changes to JSS scripts in your dev/test environment, push them to a git repository, and then export a tagged copy to your JSS, complete with the git changelog in the 'Notes' field. Reverting a change is as easy as exporting the previous tagged version.

Templating of some important values is also supported, so your scripts automatically contain details of the last change, and where they can be found in source control.


Installation / Usage
--------------------

NB: the python-jss module is a requirement. If manually installing, you'll need to make sure it is present. 
Installing via pip should take care of this for you.

Install via pip:

    ``pip install git2jss``
    
    ``pip install cryptography``

Or manually

    ``git clone https://github.com/gkluoe/git2jss.git``
    
    ``python setup.py install``
    
Contributing
------------

Issues and pull requests are very welcome!

Examples
--------
You can use it like this::

  # Create a new tag, v1.0.1, and export my_great_script.py to a script object of the same name on the JSS
  git2jss --file my_great_script.py --create --tag v1.0.1

  # Push script localscript.sh to a script object on the JSS called do_something_great.sh, using the existing tag v0.0.9
  git2jss --file localscript.sh --name do_something_great.sh

  # Push every script in the current folder which has a script object on the server with a matching name
  git2jss --all --tag v1.0.2

  # Show information about the currently configured JSS
  git2jss --jss-info
