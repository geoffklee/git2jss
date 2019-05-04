#!/bin/bash
# Use this script to generate a new relese
# It will create a new tag push it to github and push a source distribution to pypi

# Bail immediately if anything fails
set -Eeuo pipefail

pip install bumpversion twine

release_level=${1}

if [ "${release_level}" == "major" ] ||\
   [ "${release_level}" == "minor" ] ||\
   [ "${release_level}" == "patch" ]
then
   bump_args="--list ${release_level}"
elif [ ! -z "${release_level}" ]
then
   bump_args="--list --new-version=${release_level} patch" 
else 
   echo "Specify major, minor or patch"
   exit 1
fi

git checkout master

git pull

#python setup.py test

# First bump a new version - this creates a new git tag
new_version="$(bumpversion --tag ${bump_args} | awk -F '=' '/new_version/ {print $2}')"

# Commit the tag
git push origin v"${new_version}"

rm -rf dist/*

# Build source distribution
python setup.py sdist
python setup.py bdist_wheel

# Upload to pypi
twine upload dist/*

# Build a package using autopkg
autopkg run --verbose -d autopkg-recipe git2jss.pkg
