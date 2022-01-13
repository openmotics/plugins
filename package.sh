#!/bin/bash

set -eu

if [[ $# -eq 1 ]]
then
    plugin=$1
    version=''
elif [[ $# -eq 2 ]]
then
    plugin=$1
    version=$2
else
    echo """Invalid number of arguments
    Usage: ./package.sh <plugin> [<version>]
    <plugin> is the name of the plugin, located in the directory with the same name
    <version> (optional) is used to update main.py of the plugin"""
    exit 1
fi

if [ $(uname -s) == 'Darwin' ]
then
  tarcmd="tar -L"
  md5cmd="md5"
else
  tarcmd="tar -h"
  md5cmd='md5sum'
fi

cd ${plugin}

find . -type f -name "*.py[co]" -delete
find . -type d -name "__pycache__" -delete

if [[ -z "$version" ]]
then
    version=`cat main.py | grep version | cut -d "\"" -f 2 | cut -d "'" -f 2 | head -n 1`
fi

if ! [[ $version =~ ^([0-9]+\.)([0-9]+\.)(\*|[0-9]+)$ ]]
then
  echo "Not a valid plugin version $version"
  exit 2
fi

tar_file=${plugin}_${version}.tgz
md5_file=${plugin}_${version}.md5

${tarcmd} -czf ${tar_file} *
mv ${tar_file} ..

cd ..

${md5cmd} ${tar_file} > ${md5_file}
cat ${md5_file}
