#!/bin/bash
if [ $# -ne 3 ]
then
  echo "Usage: ./`basename $0` <package> <ip/hostname of gateway> <username>"
else
  if [ $(uname -s) = 'Darwin' ]
  then
    checksum=`md5 $1 | cut -d ' ' -f 4`
    sedcmd='sed -E'
  else
    checksum=`md5sum $1 | cut -d ' ' -f 1`
    sedcmd='sed -r'
  fi

  read -s -p "Enter password: " password
  echo
  login=`curl -sk -X GET "https://$2/login?username=$3&password=$password"`
  success=`echo $login | $sedcmd 's/(.+)"success": *([a-z]+)(.+)/\2/'`

  if [ "$success" = "true" ]
  then
    token=`echo $login | $sedcmd 's/(.+)"token": *"([a-z,0-9]+)"(.+)/\2/'`
    result=`curl -sk --form "package_data=@$1" --form md5=$checksum --form token=$token -X POST "https://$2/install_plugin"`
    success=`echo $result | $sedcmd 's/(.+)"success": *([a-z]+)(.+)/\2/'`
    if [ "$success" = "true" ]
    then
      echo "Publish succeeded"
    else
      error=`echo $result | $sedcmd 's/"msg": *"([^"]+)/\1/'`
      echo "Publish failed: $error"
    fi
  else
    echo "Login failed"
  fi
fi
