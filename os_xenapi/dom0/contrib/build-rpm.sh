#!/bin/bash
#
# Copyright 2013 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

# Save trace setting
_XTRACE_XENSERVER=$(set +o | grep xtrace)
set -o xtrace

# THIS_DIR is directory that build-rpm.sh located
THIS_DIR=$(dirname $(readlink -f "$0"))
RPMBUILD_DIR=$THIS_DIR/rpmbuild
PACKAGE="xenapi-plugins"

if [ ! -d $RPMBUILD_DIR ]; then
    echo $RPMBUILD_DIR is missing
    exit 1
fi

tee version.py << EOF
import pbr.version
version_str = pbr.version.VersionInfo('os-xenapi').release_string()
print version_str
EOF

VERSION=$(python version.py)

for dir in BUILD BUILDROOT SRPMS RPMS SOURCES; do
    rm -rf $RPMBUILD_DIR/$dir
    mkdir -p $RPMBUILD_DIR/$dir
done

rm -rf /tmp/$PACKAGE
mkdir /tmp/$PACKAGE
cp -r ../etc/xapi.d /tmp/$PACKAGE
tar czf $RPMBUILD_DIR/SOURCES/$PACKAGE.tar.gz -C /tmp $PACKAGE

rpmbuild -ba --nodeps --define "_topdir $RPMBUILD_DIR"  \
    --define "version $VERSION" \
    $RPMBUILD_DIR/SPECS/$PACKAGE.spec

# Restore xtrace
$_XTRACE_XENSERVER