#!/bin/sh
cd $1
tar -czf $1.tgz *
mv $1.tgz ..
cd ..
md5sum $1.tgz
