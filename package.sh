#!/bin/bash

set -eu

if [[ $# -ne 2 ]]
then
    echo """Invalid number of arguments
    Usage: ./package.sh <plugin> <version>
    <plugin> is the name of the plugin, located in the directory with the same name
    <version> is used to update main.py of the plugin"""
    exit 1
fi

plugin=$1
version=$2
tar_file=${plugin}_${version}.tgz
md5_file=${plugin}_${version}.md5

if [ $(uname -s) == 'Darwin' ]
then
  md5cmd='md5'
else
  md5cmd='md5sum'
fi


cd ${plugin}
sed -i '' -E "s/version = '([0-9]+\.[0-9]+\.[0-9]+)'/version = '$version'/" main.py
tar -cLzf ${tar_file} *
mv ${tar_file} ..
cd ..
${md5cmd} ${tar_file} > ${md5_file}
cat ${md5_file}
