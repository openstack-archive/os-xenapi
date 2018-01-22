#!/bin/bash
set -e

REPO_NAME="CentOS-Base.repo"
REPO_PATH="/etc/yum.repos.d/$REPO_NAME"
TMP_REPO_DIR="/tmp/repo/"
TMP_REPO_PATH=$TMP_REPO_DIR$REPO_NAME
PKG_NAME="conntrack-tools"

if ! yum list installed $PKG_NAME; then
    mkdir -p $TMP_REPO_DIR
    cp $REPO_PATH $TMP_REPO_DIR
    sed -i s/#baseurl=/baseurl=/g $TMP_REPO_PATH
    centos_ver=$(yum version nogroups |grep Installed | cut -d' ' -f 2 | cut -d'/' -f 1 | cut -d'-' -f 1)
    yum install -y -c $TMP_REPO_PATH --enablerepo=base --releasever=$centos_ver $PKG_NAME
    rm -rf $TMP_REPO_DIR
fi
