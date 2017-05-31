#!/bin/bash

# This script is run by install_os_domU.sh
#
# It modifies the ubuntu image created by install_os_domU.sh
# and previously moodified by prepare_guest_template.sh
#
# This script is responsible for:
# - pushing in the DevStack code
# - creating run.sh, to run the code on boot
# It does this by mounting the disk image of the VM.
#
# The resultant image is then templated and started
# by install_os_domU.sh

# Exit on errors
set -o errexit
# Echo commands
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

# Source params - override xenrc params in your localrc to suite your taste
source $CONF_DIR/xenrc

#
# Parameters
#
GUEST_NAME="$1"

function _print_interface_config {
    local device_nr
    local ip_address
    local netmask

    device_nr="$1"
    ip_address="$2"
    netmask="$3"

    local device

    device="eth${device_nr}"

    echo "auto $device"
    if [ "$ip_address" = "dhcp" ]; then
        echo "iface $device inet dhcp"
    else
        echo "iface $device inet static"
        echo "  address $ip_address"
        echo "  netmask $netmask"
    fi

    # Turn off tx checksumming for better performance
    echo "  post-up ethtool -K $device tx off"
}

function print_interfaces_config {
    echo "auto lo"
    echo "iface lo inet loopback"

    _print_interface_config $PUB_DEV_NR $PUB_IP $PUB_NETMASK
    _print_interface_config $VM_DEV_NR $VM_IP $VM_NETMASK
    _print_interface_config $MGT_DEV_NR $MGT_IP $MGT_NETMASK
}

#
# Mount the VDI
#
STAGING_DIR=$($TOP_DIR/scripts/manage-vdi open $GUEST_NAME 0 1 | grep -o "/tmp/tmp.[[:alnum:]]*")
add_on_exit "$TOP_DIR/scripts/manage-vdi close $GUEST_NAME 0 1"

# Make sure we have a stage
if [ ! -d $STAGING_DIR/etc ]; then
    echo "Stage is not properly set up!"
    exit 1
fi

# Only support DHCP for now - don't support how different versions of Ubuntu handle resolv.conf
if [ "$MGT_IP" != "dhcp" ] && [ "$PUB_IP" != "dhcp" ]; then
    echo "Configuration without DHCP not supported"
    exit 1
fi

# Configure the hostname
echo $GUEST_NAME > $STAGING_DIR/etc/hostname

# Hostname must resolve for rabbit
HOSTS_FILE_IP=$PUB_IP
if [ $MGT_IP != "dhcp" ]; then
    HOSTS_FILE_IP=$MGT_IP
fi
cat <<EOF >$STAGING_DIR/etc/hosts
$HOSTS_FILE_IP $GUEST_NAME
127.0.0.1 localhost localhost.localdomain
EOF

# Configure the network
print_interfaces_config > $STAGING_DIR/etc/network/interfaces
