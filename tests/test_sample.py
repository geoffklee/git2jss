from pylint import epylint as lint

def test_lint():
    (out, err) = lint.py_run('git2jss', return_std="True")
    result = out.read()
    if not '10.00/10' in result.split(" "):
       print "Failed pylint!"
       print result 
       assert False
    

