#!/bin/sh
cd $1
version=`cat main.py | grep version | cut -d "\"" -f 2 | cut -d "'" -f 2`
tgzname=$1_$version
tar -czf $tgzname.tgz *
mv $tgzname.tgz ..
cd ..
md5sum $tgzname.tgz
