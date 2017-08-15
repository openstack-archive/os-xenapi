#!/bin/bash

# This script must be run on a XenServer or XCP machine
#
# It creates a clean ubuntu VM template
#
# For more details see: README.md

set -o errexit
set -o nounset
set -o xtrace

export LC_ALL=C

# directory settings
THIS_DIR=$(cd $(dirname "$0") && pwd)
SCRIPT_DIR="$THIS_DIR/scripts"
COMM_DIR="$THIS_DIR/common"
CONF_DIR="$THIS_DIR/conf"

# Include onexit commands
. $SCRIPT_DIR/on_exit.sh

# xapi functions

. $COMM_DIR/functions

# Source params - override xenrc params in your local.conf to suit your taste
source $CONF_DIR/xenrc

#
# Prepare Dom0
# including installing XenAPI plugins
#

cd $THIS_DIR

# Check if multiple hosts listed
if have_multiple_hosts; then
    cat >&2 << EOF
Info: multiple hosts found. This might mean that the XenServer is a member
of a pool.
EOF
fi

#
# Configure Networking
#

host_uuid=$(get_current_host_uuid)

MGT_NETWORK=`xe pif-list management=true host-uuid=$host_uuid params=network-uuid minimal=true`
HOST_MGT_BRIDGE_OR_NET_NAME=`xe network-list uuid=$MGT_NETWORK params=bridge minimal=true`

setup_network "$HOST_MGT_BRIDGE_OR_NET_NAME"

if ! xenapi_is_listening_on "$HOST_MGT_BRIDGE_OR_NET_NAME"; then
    cat >&2 << EOF
ERROR: XenAPI does not have an assigned IP address on the management network.
please review your XenServer network configuration file.
EOF
    exit 1
fi

HOST_IP=$(xenapi_ip_on "$HOST_MGT_BRIDGE_OR_NET_NAME")

# Set up ip forwarding, but skip on xcp-xapi
if [ -a /etc/sysconfig/network ]; then
    if ! grep -q "FORWARD_IPV4=YES" /etc/sysconfig/network; then
        # FIXME: This doesn't work on reboot!
        echo "FORWARD_IPV4=YES" >> /etc/sysconfig/network
    fi
fi
# Also, enable ip forwarding in rc.local, since the above trick isn't working
if ! grep -q  "echo 1 >/proc/sys/net/ipv4/ip_forward" /etc/rc.local; then
    echo "echo 1 >/proc/sys/net/ipv4/ip_forward" >> /etc/rc.local
fi
# Enable ip forwarding at runtime as well
echo 1 > /proc/sys/net/ipv4/ip_forward


#
# Shutdown previous runs
#

DO_SHUTDOWN=${DO_SHUTDOWN:-1}
CLEAN_TEMPLATES=${CLEAN_TEMPLATES:-false}
if [ "$DO_SHUTDOWN" = "1" ]; then
    # Shutdown all VM's that created previously
    clean_templates_arg=""
    if $CLEAN_TEMPLATES; then
        clean_templates_arg="--remove-templates"
    fi
    $SCRIPT_DIR/uninstall-os-vpx.sh $clean_templates_arg

    # Destroy any instances that were launched
    for uuid in `xe vm-list resident-on=$host_uuid | grep -1 instance | grep uuid | sed "s/.*\: //g"`; do
        echo "Shutting down nova instance $uuid"
        xe vm-uninstall uuid=$uuid force=true
    done

    # Destroy orphaned vdis
    for uuid in `xe vdi-list | grep -1 Glance | grep uuid | sed "s/.*\: //g"`; do
        xe vdi-destroy uuid=$uuid
    done
fi


#
# Create Ubuntu VM template
# and/or create VM from template
#
templateuuid=$(get_template $TNAME $host_uuid)

if [ -z "$templateuuid" ]; then
    #
    # Install Ubuntu over network
    #
    UBUNTU_INST_BRIDGE_OR_NET_NAME=${UBUNTU_INST_BRIDGE_OR_NET_NAME:-"$HOST_MGT_BRIDGE_OR_NET_NAME"}

    # always update the preseed file, incase we have a newer one
    PRESEED_URL=${PRESEED_URL:-""}
    if [ -z "$PRESEED_URL" ]; then
        PRESEED_URL="${HOST_IP}/ubuntupreseed.cfg"

        HTTP_SERVER_LOCATION="/opt/xensource/www"
        if [ ! -e $HTTP_SERVER_LOCATION ]; then
            HTTP_SERVER_LOCATION="/var/www/html"
            mkdir -p $HTTP_SERVER_LOCATION
        fi

        # Copy the tools DEB to the XS web server
        XS_TOOLS_URL="https://github.com/downloads/citrix-openstack/warehouse/xe-guest-utilities_5.6.100-651_amd64.deb"
        ISO_DIR="/opt/xensource/packages/iso"
        if [ -e "$ISO_DIR" ]; then
            TOOLS_ISO=$(ls -1 $ISO_DIR/*-tools-*.iso | head -1)
            TMP_DIR=/tmp/temp.$RANDOM
            mkdir -p $TMP_DIR
            mount -o loop $TOOLS_ISO $TMP_DIR
            # the target deb package maybe *amd64.deb or *all.deb,
            # so use *amd64.deb by default. If it doesn't exist,
            # then use *all.deb.
            DEB_FILE=$(ls $TMP_DIR/Linux/*amd64.deb || ls $TMP_DIR/Linux/*all.deb)
            cp $DEB_FILE $HTTP_SERVER_LOCATION
            umount $TMP_DIR
            rmdir $TMP_DIR
            XS_TOOLS_URL=${HOST_IP}/$(basename $DEB_FILE)
        fi

        cp -f $CONF_DIR/ubuntupreseed.cfg $HTTP_SERVER_LOCATION
        cp -f $SCRIPT_DIR/ubuntu_latecommand.sh $HTTP_SERVER_LOCATION/latecommand.sh

        sed \
            -e "s,\(d-i mirror/http/hostname string\).*,\1 $UBUNTU_INST_HTTP_HOSTNAME,g" \
            -e "s,\(d-i mirror/http/directory string\).*,\1 $UBUNTU_INST_HTTP_DIRECTORY,g" \
            -e "s,\(d-i mirror/http/proxy string\).*,\1 $UBUNTU_INST_HTTP_PROXY,g" \
            -e "s,\(d-i passwd/root-password password\).*,\1 $GUEST_PASSWORD,g" \
            -e "s,\(d-i passwd/root-password-again password\).*,\1 $GUEST_PASSWORD,g" \
            -e "s,\(d-i preseed/late_command string\).*,\1 in-target mkdir -p /tmp; in-target wget --no-proxy ${HOST_IP}/latecommand.sh -O /root/latecommand.sh; in-target bash /root/latecommand.sh,g" \
            -i "${HTTP_SERVER_LOCATION}/ubuntupreseed.cfg"

        sed \
            -e "s,@XS_TOOLS_URL@,$XS_TOOLS_URL,g" \
            -i "${HTTP_SERVER_LOCATION}/latecommand.sh"
    fi

    # Update the template
    $SCRIPT_DIR/install_ubuntu_template.sh $PRESEED_URL

    # create a new VM from the given template with eth0 attached to the given
    # network
    $SCRIPT_DIR/install-os-vpx.sh \
        -t "$UBUNTU_INST_TEMPLATE_NAME" \
        -n "$UBUNTU_INST_BRIDGE_OR_NET_NAME" \
        -l "$GUEST_NAME"

    set_vm_memory "$GUEST_NAME" "1024"

    xe vm-start vm="$GUEST_NAME" on=$host_uuid

    # wait for install to finish
    wait_for_VM_to_halt "$GUEST_NAME"

    # set VM to restart after a reboot
    vm_uuid=$(xe_min vm-list name-label="$GUEST_NAME")
    xe vm-param-set actions-after-reboot=Restart uuid="$vm_uuid"

    # Make template from VM
    snuuid=$(xe vm-snapshot vm="$GUEST_NAME" new-name-label="$SNAME_TEMPLATE")
    xe snapshot-clone uuid=$snuuid new-name-label="$TNAME"
    xe vm-uninstall vm="$GUEST_NAME" force=true
else
    echo "the template has already exist"
fi
template_uuid=$(get_template "$TNAME" $host_uuid)
exist_val=$(xe template-param-get uuid=$template_uuid param-name=PV-args)
if [ -n "$exist_val" ];
    then
    xe template-param-set uuid=$template_uuid PV-args=""
fi
set +x
echo "################################################################################"
echo ""
echo "Template create done!"
echo "################################################################################"
