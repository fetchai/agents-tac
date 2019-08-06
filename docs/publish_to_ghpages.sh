#!/bin/bash

if [ -z $1 ]
then
	echo "Please provide a tag argument."
    exit 1;
fi

STATUS="$(git status)"

if ! [[ $STATUS == *"nothing to commit, working tree clean"* ]]
then
    echo "The working directory is dirty. Please commit any pending changes."
    exit 1;
fi

set -e

echo "Deleting old publication"
rm -rf _build

echo "Cloning gh-pages branch"
mkdir _build -p
cd _build
git clone --single-branch --branch gh-pages git@github.com:fetchai/agents-tac.git html
cd ..

echo "Building docs"
sphinx-apidoc -o reference/api/ ../tac/
make html
cd _build/html

echo "Pushing to gh-pages branch"
git add --all && git commit -m "Publish docs ($1)"
git tag $1
git push origin gh-pages

echo "Delete local repo"
cd ../../
make clean
