#!/bin/bash

# This script must be run on a XenServer or XCP machine
#
# It creates a DomU VM that runs OpenStack services
#
# For more details see: README.md

set -o errexit
set -o nounset
set -o xtrace

export LC_ALL=C

XENAPI_CONNECTION_IP="$1"

# This directory
THIS_DIR=$(cd $(dirname "$0") && pwd)
SCRIPT_DIR="$THIS_DIR/scripts"
COMM_DIR="$THIS_DIR/common"
CONF_DIR="$THIS_DIR/conf"

. $COMM_DIR/functions

# Source params
source $CONF_DIR/xenrc

#
# Prepare VM for DevStack
#

#
# Configure Networking
#

MGT_NETWORK=`xe pif-list management=true params=network-uuid minimal=true`
MGT_BRIDGE_OR_NET_NAME=`xe network-list uuid=$MGT_NETWORK params=bridge minimal=true`

setup_network "$VM_BRIDGE_OR_NET_NAME"
setup_network "$MGT_BRIDGE_OR_NET_NAME"
setup_network "$PUB_BRIDGE_OR_NET_NAME"

if parameter_is_specified "FLAT_NETWORK_BRIDGE"; then
    if [ "$(bridge_for "$VM_BRIDGE_OR_NET_NAME")" != "$(bridge_for "$FLAT_NETWORK_BRIDGE")" ]; then
        cat >&2 << EOF
ERROR: FLAT_NETWORK_BRIDGE is specified in localrc file, and either no network
found on XenServer by searching for networks by that value as name-label or
bridge name or the network found does not match the network specified by
VM_BRIDGE_OR_NET_NAME. Please check your localrc file.
EOF
        exit 1
    fi
fi

if ! xenapi_is_listening_on "$MGT_BRIDGE_OR_NET_NAME"; then
    cat >&2 << EOF
ERROR: XenAPI does not have an assigned IP address on the management network.
please review your XenServer network configuration / localrc file.
EOF
    exit 1
fi

HOST_IP=$(xenapi_ip_on "$MGT_BRIDGE_OR_NET_NAME")

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

#install the previous ubuntu VM

vm_exist=$(xe vm-list name-label="$DEV_STACK_DOMU_NAME" --minimal)
if [ "$vm_exist" != "" ]
then
    echo "Uninstall the previous VM"
    xe vm-uninstall vm="$DEV_STACK_DOMU_NAME" force=true
fi

echo "Install a new ubuntu VM according to previous template"

vm_uuid=$(xe vm-install template="$TNAME" new-name-label="$DEV_STACK_DOMU_NAME")

xe vm-param-set other-config:os-vpx=true uuid="$vm_uuid"

# Install XenServer tools, and other such things
$SCRIPT_DIR/prepare_guest_template.sh "$DEV_STACK_DOMU_NAME"

# Set virtual machine parameters
set_vm_memory "$DEV_STACK_DOMU_NAME" "$OSDOMU_MEM_MB"

# Max out VCPU count for better performance
max_vcpus "$DEV_STACK_DOMU_NAME"

# Wipe out all network cards
destroy_all_vifs_of "$DEV_STACK_DOMU_NAME"

# Add only one interface to prepare the guest template
add_interface "$DEV_STACK_DOMU_NAME" "$MGT_BRIDGE_OR_NET_NAME" "0"

# start the VM to run the prepare steps
xe vm-start vm="$DEV_STACK_DOMU_NAME"

# Wait for prep script to finish and shutdown system
wait_for_VM_to_halt "$XENAPI_CONNECTION_IP" "$DEV_STACK_DOMU_NAME"

## Setup network cards
# Wipe out all
destroy_all_vifs_of "$DEV_STACK_DOMU_NAME"
# Tenant network
add_interface "$DEV_STACK_DOMU_NAME" "$VM_BRIDGE_OR_NET_NAME" "$VM_DEV_NR"
# Management network
add_interface "$DEV_STACK_DOMU_NAME" "$MGT_BRIDGE_OR_NET_NAME" "$MGT_DEV_NR"
# Public network
add_interface "$DEV_STACK_DOMU_NAME" "$PUB_BRIDGE_OR_NET_NAME" "$PUB_DEV_NR"

#
# config network
#
$SCRIPT_DIR/persist_domU_interfaces.sh "$DEV_STACK_DOMU_NAME"


FLAT_NETWORK_BRIDGE="${FLAT_NETWORK_BRIDGE:-$(bridge_for "$VM_BRIDGE_OR_NET_NAME")}"
append_kernel_cmdline "$DEV_STACK_DOMU_NAME" "flat_network_bridge=${FLAT_NETWORK_BRIDGE}"

# Add a separate xvdb, if it was requested
if [[ "0" != "$XEN_XVDB_SIZE_GB" ]]; then
    vm=$(xe vm-list name-label="$DEV_STACK_DOMU_NAME" --minimal)

    # Add a new disk
    localsr=$(get_local_sr)
    extra_vdi=$(xe vdi-create \
        name-label=xvdb-added-by-devstack \
        virtual-size="${XEN_XVDB_SIZE_GB}GiB" \
        sr-uuid=$localsr type=user)
    xe vbd-create vm-uuid=$vm vdi-uuid=$extra_vdi device=1
fi

#
# Run DevStack VM
#
xe vm-start vm="$DEV_STACK_DOMU_NAME"

# Get hold of the Management IP of OpenStack VM
OS_VM_MANAGEMENT_ADDRESS=$MGT_IP
if [ $OS_VM_MANAGEMENT_ADDRESS == "dhcp" ]; then
    OS_VM_MANAGEMENT_ADDRESS=$(find_ip_by_name $DEV_STACK_DOMU_NAME $MGT_DEV_NR)
fi

# Create an ssh-keypair, and set it up for dom0 user
rm -f /root/dom0key /root/dom0key.pub
ssh-keygen -f /root/dom0key -P "" -C "dom0"
DOMID=$(get_domid "$DEV_STACK_DOMU_NAME")

xenstore-write /local/domain/$DOMID/authorized_keys/$DOMZERO_USER "$(cat /root/dom0key.pub)"
xenstore-chmod -u /local/domain/$DOMID/authorized_keys/$DOMZERO_USER r$DOMID

function run_on_appliance {
    ssh \
        -i /root/dom0key \
        -o UserKnownHostsFile=/dev/null \
        -o StrictHostKeyChecking=no \
        -o BatchMode=yes \
        "$DOMZERO_USER@$OS_VM_MANAGEMENT_ADDRESS" "$@"
}

# Wait until we can log in to the appliance
while ! run_on_appliance true; do
    sleep 1
done

# Remove authenticated_keys updater cronjob
echo "" | run_on_appliance crontab -

# Generate a passwordless ssh key for domzero user
echo "ssh-keygen -f /home/$DOMZERO_USER/.ssh/id_rsa -C $DOMZERO_USER@appliance -N \"\" -q" | run_on_appliance

# Authenticate that user to dom0
run_on_appliance cat /home/$DOMZERO_USER/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys

echo "################################################################################"
echo ""
echo "VM configuration done!"
echo "################################################################################"
