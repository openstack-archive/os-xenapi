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

# This directory
THIS_DIR=$(cd $(dirname "$0") && pwd)

# Include onexit commands
. $THIS_DIR/scripts/on_exit.sh

# xapi functions
. $THIS_DIR/functions

#
# Get Settings
#
TOP_DIR=$(cd $THIS_DIR/../ && pwd)
source $TOP_DIR/functions-common
rm -f $TOP_DIR/.localrc.auto
extract_localrc_section $TOP_DIR/local.conf $TOP_DIR/localrc $TOP_DIR/.localrc.auto

# Source params - override xenrc params in your localrc to suit your taste
source $THIS_DIR/xenrc

xe_min()
{
    local cmd="$1"
    shift
    xe "$cmd" --minimal "$@"
}

#
# Prepare Dom0
# including installing XenAPI plugins
#

cd $THIS_DIR

# Die if multiple hosts listed
if have_multiple_hosts; then
    cat >&2 << EOF
ERROR: multiple hosts found. This might mean that the XenServer is a member
of a pool - Exiting.
EOF
    exit 1
fi

#
# Configure Networking
#

MGT_NETWORK=`xe pif-list management=true params=network-uuid minimal=true`
MGT_BRIDGE_OR_NET_NAME=`xe network-list uuid=$MGT_NETWORK params=bridge minimal=true`

setup_network "$VM_BRIDGE_OR_NET_NAME"
setup_network "$MGT_BRIDGE_OR_NET_NAME"
setup_network "$PUB_BRIDGE_OR_NET_NAME"

# With neutron, one more network is required, which is internal to the
# hypervisor, and used by the VMs
setup_network "$XEN_INT_BRIDGE_OR_NET_NAME"

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


#
# Shutdown previous runs
#

DO_SHUTDOWN=${DO_SHUTDOWN:-1}
CLEAN_TEMPLATES=${CLEAN_TEMPLATES:-false}
if [ "$DO_SHUTDOWN" = "1" ]; then
    # Shutdown all domU's that created previously
    clean_templates_arg=""
    if $CLEAN_TEMPLATES; then
        clean_templates_arg="--remove-templates"
    fi
    ./scripts/uninstall-os-vpx.sh $clean_templates_arg

    # Destroy any instances that were launched
    for uuid in `xe vm-list | grep -1 instance | grep uuid | sed "s/.*\: //g"`; do
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

GUEST_NAME=${GUEST_NAME:-"DevStackOSDomU"}
TNAME="jeos_template_for_devstack"
SNAME_TEMPLATE="jeos_snapshot_for_devstack"
SNAME_FIRST_BOOT="before_first_boot"

function wait_for_VM_to_halt {
    set +x
    echo "Waiting for the VM to halt.  Progress in-VM can be checked with XenCenter or xl console:"
    mgmt_ip=$(echo $XENAPI_CONNECTION_URL | tr -d -c '1234567890.')
    domid=$(get_domid "$GUEST_NAME")
    echo "ssh root@$mgmt_ip \"xl console $domid\""
    while true; do
        state=$(xe_min vm-list name-label="$GUEST_NAME" power-state=halted)
        if [ -n "$state" ]; then
            break
        else
            echo -n "."
            sleep 20
        fi
    done
    set -x
}

templateuuid=$(xe template-list name-label="$TNAME")
if [ -z "$templateuuid" ]; then
    #
    # Install Ubuntu over network
    #
    UBUNTU_INST_BRIDGE_OR_NET_NAME=${UBUNTU_INST_BRIDGE_OR_NET_NAME:-"$MGT_BRIDGE_OR_NET_NAME"}

    # always update the preseed file, incase we have a newer one
    PRESEED_URL=${PRESEED_URL:-""}
    if [ -z "$PRESEED_URL" ]; then
        PRESEED_URL="${HOST_IP}/devstackubuntupreseed.cfg"

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

        cp -f $THIS_DIR/devstackubuntupreseed.cfg $HTTP_SERVER_LOCATION
        cp -f $THIS_DIR/devstackubuntu_latecommand.sh $HTTP_SERVER_LOCATION/latecommand.sh

        sed \
            -e "s,\(d-i mirror/http/hostname string\).*,\1 $UBUNTU_INST_HTTP_HOSTNAME,g" \
            -e "s,\(d-i mirror/http/directory string\).*,\1 $UBUNTU_INST_HTTP_DIRECTORY,g" \
            -e "s,\(d-i mirror/http/proxy string\).*,\1 $UBUNTU_INST_HTTP_PROXY,g" \
            -e "s,\(d-i passwd/root-password password\).*,\1 $GUEST_PASSWORD,g" \
            -e "s,\(d-i passwd/root-password-again password\).*,\1 $GUEST_PASSWORD,g" \
            -e "s,\(d-i preseed/late_command string\).*,\1 in-target mkdir -p /tmp; in-target wget --no-proxy ${HOST_IP}/latecommand.sh -O /root/latecommand.sh; in-target bash /root/latecommand.sh,g" \
            -i "${HTTP_SERVER_LOCATION}/devstackubuntupreseed.cfg"

        sed \
            -e "s,@XS_TOOLS_URL@,$XS_TOOLS_URL,g" \
            -i "${HTTP_SERVER_LOCATION}/latecommand.sh"
    fi

    # Update the template
    $THIS_DIR/scripts/install_ubuntu_template.sh $PRESEED_URL

    # create a new VM from the given template with eth0 attached to the given
    # network
    $THIS_DIR/scripts/install-os-vpx.sh \
        -t "$UBUNTU_INST_TEMPLATE_NAME" \
        -n "$UBUNTU_INST_BRIDGE_OR_NET_NAME" \
        -l "$GUEST_NAME"

    set_vm_memory "$GUEST_NAME" "1024"

    xe vm-start vm="$GUEST_NAME"

    # wait for install to finish
    wait_for_VM_to_halt

    # set VM to restart after a reboot
    vm_uuid=$(xe_min vm-list name-label="$GUEST_NAME")
    xe vm-param-set actions-after-reboot=Restart uuid="$vm_uuid"

    # Make template from VM
    snuuid=$(xe vm-snapshot vm="$GUEST_NAME" new-name-label="$SNAME_TEMPLATE")
    xe snapshot-clone uuid=$snuuid new-name-label="$TNAME"
else
    #
    # Template already installed, create VM from template
    #
    vm_uuid=$(xe vm-install template="$TNAME" new-name-label="$GUEST_NAME")
fi

if [ -n "${EXIT_AFTER_JEOS_INSTALLATION:-}" ]; then
    echo "User requested to quit after JEOS installation"
    exit 0
fi

#
# Prepare VM for DevStack
#
xe vm-param-set other-config:os-vpx=true uuid="$vm_uuid"

# Install XenServer tools, and other such things
$THIS_DIR/prepare_guest_template.sh "$GUEST_NAME"

# Set virtual machine parameters
set_vm_memory "$GUEST_NAME" "$OSDOMU_MEM_MB"

# Max out VCPU count for better performance
max_vcpus "$GUEST_NAME"

# Wipe out all network cards
destroy_all_vifs_of "$GUEST_NAME"

# Add only one interface to prepare the guest template
add_interface "$GUEST_NAME" "$MGT_BRIDGE_OR_NET_NAME" "0"

# start the VM to run the prepare steps
xe vm-start vm="$GUEST_NAME"

# Wait for prep script to finish and shutdown system
wait_for_VM_to_halt

## Setup network cards
# Wipe out all
destroy_all_vifs_of "$GUEST_NAME"
# Tenant network
add_interface "$GUEST_NAME" "$VM_BRIDGE_OR_NET_NAME" "$VM_DEV_NR"
# Management network
add_interface "$GUEST_NAME" "$MGT_BRIDGE_OR_NET_NAME" "$MGT_DEV_NR"
# Public network
add_interface "$GUEST_NAME" "$PUB_BRIDGE_OR_NET_NAME" "$PUB_DEV_NR"

#
# Inject DevStack inside VM disk
#
$THIS_DIR/build_xva.sh "$GUEST_NAME"

# Attach a network interface for the integration network (so that the bridge
# is created by XenServer). This is required for Neutron. Also pass that as a
# kernel parameter for DomU
attach_network "$XEN_INT_BRIDGE_OR_NET_NAME"

XEN_INTEGRATION_BRIDGE_DEFAULT=$(bridge_for "$XEN_INT_BRIDGE_OR_NET_NAME")
append_kernel_cmdline \
    "$GUEST_NAME" \
    "xen_integration_bridge=${XEN_INTEGRATION_BRIDGE_DEFAULT}"

FLAT_NETWORK_BRIDGE="${FLAT_NETWORK_BRIDGE:-$(bridge_for "$VM_BRIDGE_OR_NET_NAME")}"
append_kernel_cmdline "$GUEST_NAME" "flat_network_bridge=${FLAT_NETWORK_BRIDGE}"

# Add a separate xvdb, if it was requested
if [[ "0" != "$XEN_XVDB_SIZE_GB" ]]; then
    vm=$(xe vm-list name-label="$GUEST_NAME" --minimal)

    # Add a new disk
    localsr=$(get_local_sr)
    extra_vdi=$(xe vdi-create \
        name-label=xvdb-added-by-devstack \
        virtual-size="${XEN_XVDB_SIZE_GB}GiB" \
        sr-uuid=$localsr type=user)
    xe vbd-create vm-uuid=$vm vdi-uuid=$extra_vdi device=1
fi

# create a snapshot before the first boot
# to allow a quick re-run with the same settings
xe vm-snapshot vm="$GUEST_NAME" new-name-label="$SNAME_FIRST_BOOT"

#
# Run DevStack VM
#
xe vm-start vm="$GUEST_NAME"

function ssh_no_check {
    ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "$@"
}

# Get hold of the Management IP of OpenStack VM
OS_VM_MANAGEMENT_ADDRESS=$MGT_IP
if [ $OS_VM_MANAGEMENT_ADDRESS == "dhcp" ]; then
    OS_VM_MANAGEMENT_ADDRESS=$(find_ip_by_name $GUEST_NAME $MGT_DEV_NR)
fi

# Get hold of the Service IP of OpenStack VM
if [ $HOST_IP_IFACE == "eth${MGT_DEV_NR}" ]; then
    OS_VM_SERVICES_ADDRESS=$MGT_IP
    if [ $MGT_IP == "dhcp" ]; then
        OS_VM_SERVICES_ADDRESS=$(find_ip_by_name $GUEST_NAME $MGT_DEV_NR)
    fi
else
    OS_VM_SERVICES_ADDRESS=$PUB_IP
    if [ $PUB_IP == "dhcp" ]; then
        OS_VM_SERVICES_ADDRESS=$(find_ip_by_name $GUEST_NAME $PUB_DEV_NR)
    fi
fi

# Create an ssh-keypair, and set it up for dom0 user
rm -f /root/dom0key /root/dom0key.pub
ssh-keygen -f /root/dom0key -P "" -C "dom0"
DOMID=$(get_domid "$GUEST_NAME")

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

# If we have copied our ssh credentials, use ssh to monitor while the installation runs
WAIT_TILL_LAUNCH=${WAIT_TILL_LAUNCH:-1}
COPYENV=${COPYENV:-1}
if [ "$WAIT_TILL_LAUNCH" = "1" ]  && [ -e ~/.ssh/id_rsa.pub  ] && [ "$COPYENV" = "1" ]; then
    set +x

    echo "VM Launched - Waiting for run.sh"
    while ! ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "test -e /opt/stack/run_sh.pid"; do
        sleep 10
    done
    echo -n "devstack service is running, waiting for stack.sh to start logging..."

    pid=`ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "cat /opt/stack/run_sh.pid"`
    if [ -n "$SCREEN_LOGDIR" ]; then
        while ! ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "test -e ${SCREEN_LOGDIR}/stack.log"; do
            sleep 10
        done

        ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "tail --pid $pid -n +1 -f ${SCREEN_LOGDIR}/stack.log"
    else
        echo -n "SCREEN_LOGDIR not set; just waiting for process $pid to finish"
        ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "wait $pid"
    fi

    set -x
    # Fail if devstack did not succeed
    ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS 'test -e /opt/stack/runsh.succeeded'

    set +x
    echo "################################################################################"
    echo ""
    echo "All Finished!"
    echo "You can visit the OpenStack Dashboard"
    echo "at http://$OS_VM_SERVICES_ADDRESS, and contact other services at the usual ports."
else
    set +x
    echo "################################################################################"
    echo ""
    echo "All Finished!"
    echo "Now, you can monitor the progress of the stack.sh installation by "
    echo "looking at the console of your domU / checking the log files."
    echo ""
    echo "ssh into your domU now: 'ssh stack@$OS_VM_MANAGEMENT_ADDRESS' using your password"
    echo "and then do: 'sudo systemctl status devstack' to check if devstack is still running."
    echo "Check that /opt/stack/runsh.succeeded exists"
    echo ""
    echo "When devstack completes, you can visit the OpenStack Dashboard"
    echo "at http://$OS_VM_SERVICES_ADDRESS, and contact other services at the usual ports."
fi
