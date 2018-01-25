import subprocess

def test_lint():
    try:
        subprocess.check_output(["pylint", "git2jss/__init__.py"])
    except subprocess.CalledProcessError as error:
        print(error.output)
        print("test_lint() failed.")
        assert False

