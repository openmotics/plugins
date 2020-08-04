#!/bin/sh
pyclean () {
        find . -type f -name "*.py[co]" -delete
        find . -type d -name "__pycache__" -delete
}
cd $1
pyclean
version=`cat main.py | grep version | cut -d "\"" -f 2 | cut -d "'" -f 2 | head -n 1`
tgzname=$1_$version
tar -czf $tgzname.tgz *
mv $tgzname.tgz ..
cd ..

if [ $(uname -s) == 'Darwin' ]
then
  md5cmd='md5'
else
  md5cmd='md5sum'
fi

md5sum=$($md5cmd $tgzname.tgz)

echo $md5sum > $tgzname.md5
echo $md5sum
