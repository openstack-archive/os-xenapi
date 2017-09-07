#!/bin/bash

# This script is run by install_on_xen_host.sh
#
# It modifies the ubuntu image created by install_on_xen_host.sh
# and previously moodified by prepare_guest_template.sh
#
# This script is responsible for:
# - creates a DomU VM
# - creating run.sh, to run the code on DomU boot
#
# by install_on_xen_host.sh

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

# Source params
source $CONF_DIR/xenrc

# Defaults for optional arguments
DEVSTACK_SRC=${DEVSTACK_SRC:-"https://github.com/openstack-dev/devstack"}
LOGDIR="/opt/stack/devstack_logs"
DISABLE_JOURNALING="false"

# Number of options passed to this script
REMAINING_OPTIONS="$#"
# Get optional parameters
set +e
while getopts ":d:l:r" flag; do
    REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
    case "$flag" in
        d)
            DEVSTACK_SRC="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        l)
            LOGDIR="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        r)
            DISABLE_JOURNALING="true"
            ;;
        \?)
            print_usage_and_die "Invalid option -$OPTARG"
            ;;
    esac
done
set -e

# Make sure that all options processed
if [ "0" != "$REMAINING_OPTIONS" ]; then
    print_usage_and_die "ERROR: some arguments were not recognised!"
fi

#
# Prepare VM for DevStack
#

#
# Configure Networking
#

host_uuid=$(get_current_host_uuid)

MGT_NETWORK=`xe pif-list management=true host-uuid=$host_uuid params=network-uuid minimal=true`
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

# Also, enable ip forwarding in rc.local, since the above trick isn't working
if ! grep -q  "echo 1 >/proc/sys/net/ipv4/ip_forward" /etc/rc.local; then
    echo "echo 1 >/proc/sys/net/ipv4/ip_forward" >> /etc/rc.local
fi
# Enable ip forwarding at runtime as well
echo 1 > /proc/sys/net/ipv4/ip_forward

HOST_IP=$(xenapi_ip_on "$MGT_BRIDGE_OR_NET_NAME")

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
set_vm_memory "$DEV_STACK_DOMU_NAME" "$VM_MEM_MB"

# Max out VCPU count for better performance
max_vcpus "$DEV_STACK_DOMU_NAME"

# Wipe out all network cards
destroy_all_vifs_of "$DEV_STACK_DOMU_NAME"

# Add only one interface to prepare the guest template
add_interface "$DEV_STACK_DOMU_NAME" "$MGT_BRIDGE_OR_NET_NAME" "0"

# start the VM to run the prepare steps
xe vm-start vm="$DEV_STACK_DOMU_NAME" on=$host_uuid

# Wait for prep script to finish and shutdown system
wait_for_VM_to_halt "$DEV_STACK_DOMU_NAME"

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
# persistant the VM's interfaces
#
$SCRIPT_DIR/persist_domU_interfaces.sh "$DEV_STACK_DOMU_NAME"

FLAT_NETWORK_BRIDGE="${FLAT_NETWORK_BRIDGE:-$(bridge_for "$VM_BRIDGE_OR_NET_NAME")}"
append_kernel_cmdline "$DEV_STACK_DOMU_NAME" "flat_network_bridge=${FLAT_NETWORK_BRIDGE}"

# Disable FS journaling. It would reduce disk IO, but may lead to file system
# unstable after long time use
if [ "$DISABLE_JOURNALING" = "true" ]; then
    vm_vbd=$(xe vbd-list vm-name-label=$DEV_STACK_DOMU_NAME --minimal)
    vm_vdi=$(xe vdi-list vbd-uuids=$vm_vbd --minimal)
    dom_zero_uuid=$(xe vm-list dom-id=0 resident-on=$host_uuid --minimal)
    tmp_vbd=$(xe vbd-create device=autodetect bootable=false mode=RW type=Disk vdi-uuid=$vm_vdi vm-uuid=$dom_zero_uuid)
    xe vbd-plug uuid=$tmp_vbd
    sr_id=$(get_local_sr)
    kpartx -p p -avs  /dev/sm/backend/$sr_id/$vm_vdi
    echo "********Before disable FS journaling********"
    tune2fs -l  /dev/mapper/${vm_vdi}p1 | grep "Filesystem features"
    echo "********Disable FS journaling********"
    tune2fs -O ^has_journal /dev/mapper/${vm_vdi}p1
    echo "********After disable FS journaling********"
    tune2fs -l  /dev/mapper/${vm_vdi}p1 | grep "Filesystem features"
    kpartx -p p -dvs  /dev/sm/backend/$sr_id/$vm_vdi
    xe vbd-unplug uuid=$tmp_vbd timeout=60
    xe vbd-destroy uuid=$tmp_vbd
fi

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
xe vm-start vm="$DEV_STACK_DOMU_NAME" on=$host_uuid

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

set +x
echo "################################################################################"
echo ""
echo "VM configuration done!"
echo "################################################################################"


xe vm-shutdown vm="$DEV_STACK_DOMU_NAME"
wait_for_VM_to_halt "$DEV_STACK_DOMU_NAME"
#
# Mount the VDI
#
echo "check vdi mapping"
STAGING_DIR=$($SCRIPT_DIR/manage-vdi open $DEV_STACK_DOMU_NAME 0 1 | grep -o "/tmp/tmp.[[:alnum:]]*")
add_on_exit "$SCRIPT_DIR/manage-vdi close $DEV_STACK_DOMU_NAME 0 1"
# Make sure we have a stage
if [ ! -d $STAGING_DIR/etc ]; then
    echo "ERROR:ct properly set up!"
    exit 1
fi

if [ ! -d "$STAGING_DIR/opt/stack" ]; then
    echo "ERROR: scet"
    exit -1
fi

rm -f $STAGING_DIR/opt/stack/local.conf
pif=$(xe pif-list management=true host-uuid=$host_uuid --minimal)
XENSERVER_IP=$(xe pif-param-get param-name=IP uuid=$pif)


# Create an systemd task for devstack
cat >$STAGING_DIR/etc/systemd/system/devstack.service << EOF
[Unit]
Description=Install OpenStack by DevStack

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/rm -f /opt/stack/runsh.succeeded
ExecStart=/bin/su -c "/opt/stack/run.sh" stack
StandardOutput=tty
StandardError=tty

[Install]
WantedBy=multi-user.target

EOF

if [ $? -ne 0 ]; then
echo "fatal error, install service failed."
exit 1
fi

# enable this service
rm -f $STAGING_DIR/etc/systemd/system/multi-user.target.wants/devstack.service
ln -s /etc/systemd/system/devstack.service $STAGING_DIR/etc/systemd/system/multi-user.target.wants/devstack.service

# Gracefully cp only if source file/dir exists
function cp_it {
    if [ -e $1 ] || [ -d $1 ]; then
        cp -pRL $1 $2
    fi
}

# Copy over your ssh keys and env if desired
cp_it ~/.ssh $STAGING_DIR/opt/stack/.ssh
cp_it ~/.ssh/id_rsa.pub $STAGING_DIR/opt/stack/.ssh/authorized_keys
cp_it ~/.gitconfig $STAGING_DIR/opt/stack/.gitconfig
cp_it ~/.vimrc $STAGING_DIR/opt/stack/.vimrc
cp_it ~/.bashrc $STAGING_DIR/opt/stack/.bashrc
if [ -d $DEVSTACK_SRC ]; then
  # Local repository for devstack exist, copy it to DomU
  cp_it $DEVSTACK_SRC $STAGING_DIR/opt/stack/
fi

# Journald default is to not persist logs to disk if /var/log/journal is
# not present. Update the configuration to set storage to persistent which
# will create /var/log/journal if necessary and store logs on disk. This
# avoids the situation where test runs can fill the journald ring buffer
# deleting older logs that may be important to the job.
JOURNALD_CFG=$STAGING_DIR/etc/systemd/journald.conf
if [ -f $JOURNALD_CFG ] ; then
    sed -i -e 's/#Storage=auto/Storage=persistent/' $JOURNALD_CFG
fi

# Configure run.sh
DOMU_STACK_DIR=/opt/stack
DOMU_DEV_STACK_DIR=$DOMU_STACK_DIR/devstack
cat <<EOF >$STAGING_DIR/opt/stack/run.sh
#!/bin/bash
set -eux
(
  flock -n 9 || exit 1

  sudo chown -R stack $DOMU_STACK_DIR

  cd $DOMU_STACK_DIR

  [ -e /opt/stack/runsh.succeeded ] && rm /opt/stack/runsh.succeeded
  echo \$\$ >> /opt/stack/run_sh.pid

  if [ ! -d $DOMU_DEV_STACK_DIR ]; then
  echo "Can not find the devstack source code, get it from git."
  git clone $DEVSTACK_SRC $DOMU_DEV_STACK_DIR
  fi

  cp $DOMU_STACK_DIR/local.conf $DOMU_DEV_STACK_DIR/

  cd $DOMU_DEV_STACK_DIR
  ./unstack.sh || true
  ./stack.sh

  # Got to the end - success
  touch /opt/stack/runsh.succeeded

  # Update /etc/issue
  (
      echo "OpenStack VM - Installed by DevStack"
      IPADDR=$(ip -4 address show eth0 | sed -n 's/.*inet \([0-9\.]\+\).*/\1/p')
      echo "  Management IP:   $IPADDR"
      echo -n "  Devstack run:    "
      if [ -e /opt/stack/runsh.succeeded ]; then
          echo "SUCCEEDED"
      else
          echo "FAILED"
      fi
      echo ""
  ) > /opt/stack/issue
  sudo cp /opt/stack/issue /etc/issue

  rm /opt/stack/run_sh.pid
) 9> /opt/stack/.runsh_lock
EOF

chmod 755 $STAGING_DIR/opt/stack/run.sh
if [ ! -f $TOP_DIR/local.conf ]; then
    echo "ERROR: You should prepare a local.conf and put it under $TOP_DIR"
    exit 1
fi

cp_it $TOP_DIR/local.conf $STAGING_DIR/opt/stack/local.conf
cp_it $THIS_DIR/run.sh $STAGING_DIR/opt/stack/run.sh
