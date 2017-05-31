#!/bin/bash

# This script is run by install_os_domU.sh
#
# Parameters:
# - $GUEST_NAME - hostname for the DomU VM
#
# It modifies the ubuntu image created by install_os_domU.sh
#
# This script is responsible for cusomtizing the fresh ubuntu
# image so on boot it runs the prepare_guest.sh script
# that modifies the VM so it is ready to run stack.sh.
# It does this by mounting the disk image of the VM.
#
# The resultant image is started by install_os_domU.sh,
# and once the VM has shutdown, build_xva.sh is run

set -o errexit
set -o nounset
set -o xtrace

# This directory
THIS_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR="$THIS_DIR/../"
SCRIPT_DIR="$TOP_DIR/scripts"
COMM_DIR="$TOP_DIR/common"
CONF_DIR="$TOP_DIR/conf"

# Include onexit commands
. $SCRIPT_DIR/on_exit.sh

# xapi functions
. $COMM_DIR/functions

# Source params
source $CONF_DIR/xenrc

#
# Parameters
#
GUEST_NAME="$1"

# Mount the VDI
STAGING_DIR=$($TOP_DIR/scripts/manage-vdi open $GUEST_NAME 0 1 | grep -o "/tmp/tmp.[[:alnum:]]*")
add_on_exit "$TOP_DIR/scripts/manage-vdi close $GUEST_NAME 0 1"

# Make sure we have a stage
if [ ! -d $STAGING_DIR/etc ]; then
    echo "Stage is not properly set up!"
    exit 1
fi

# Copy prepare_guest.sh to VM
mkdir -p $STAGING_DIR/opt/stack/
cp $SCRIPT_DIR/prepare_guest.sh $STAGING_DIR/opt/stack/prepare_guest.sh

# backup rc.local
cp $STAGING_DIR/etc/rc.local $STAGING_DIR/etc/rc.local.preparebackup

echo "$STAGING_DIR/etc/rc.local"
# run prepare_guest.sh on boot
cat <<EOF >$STAGING_DIR/etc/rc.local
#!/bin/sh -e
bash /opt/stack/prepare_guest.sh \\
    "$GUEST_PASSWORD" "$STACK_USER" "$DOMZERO_USER" \\
    > /opt/stack/prepare_guest.log 2>&1
EOF
echo "$STAGING_DIR/etc/apt/sources.list"
# Update ubuntu repositories
cat > $STAGING_DIR/etc/apt/sources.list << EOF
deb http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE} main restricted
deb-src http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE} main restricted
deb http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE}-updates main restricted
deb-src http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE}-updates main restricted
deb http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE} universe
deb-src http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE} universe
deb http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE}-updates universe
deb-src http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE}-updates universe
deb http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE} multiverse
deb-src http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE} multiverse
deb http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE}-updates multiverse
deb-src http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE}-updates multiverse
deb http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE}-backports main restricted universe multiverse
deb-src http://${UBUNTU_INST_HTTP_HOSTNAME}${UBUNTU_INST_HTTP_DIRECTORY} ${UBUNTU_INST_RELEASE}-backports main restricted universe multiverse

deb http://security.ubuntu.com/ubuntu ${UBUNTU_INST_RELEASE}-security main restricted
deb-src http://security.ubuntu.com/ubuntu ${UBUNTU_INST_RELEASE}-security main restricted
deb http://security.ubuntu.com/ubuntu ${UBUNTU_INST_RELEASE}-security universe
deb-src http://security.ubuntu.com/ubuntu ${UBUNTU_INST_RELEASE}-security universe
deb http://security.ubuntu.com/ubuntu ${UBUNTU_INST_RELEASE}-security multiverse
deb-src http://security.ubuntu.com/ubuntu ${UBUNTU_INST_RELEASE}-security multiverse
EOF

rm -f $STAGING_DIR/etc/apt/apt.conf
if [ -n "$UBUNTU_INST_HTTP_PROXY" ]; then
    cat > $STAGING_DIR/etc/apt/apt.conf << EOF
Acquire::http::Proxy "$UBUNTU_INST_HTTP_PROXY";
EOF
fi
