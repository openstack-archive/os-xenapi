#!/bin/bash

# This script is run by install_on_xen_host.sh
#
# It modifies the ubuntu image created by install_on_xen_host.sh
# and previously moodified by prepare_guest_template.sh
#
# This script is responsible for:
# - pushing in the DevStack code
# - creating run.sh, to run the code on boot
# It does this by mounting the disk image of the VM.
#
# The resultant image is then templated and started
# by install_on_xen_host.sh

# Exit on errors
set -o errexit
# Echo commands
set -o xtrace

# This directory
TOP_DIR=$(cd $(dirname "$0") && pwd)
SCRIPT_DIR="$TOP_DIR/scripts"
COMM_DIR="$TOP_DIR/common"
CONF_DIR="$TOP_DIR/conf"

XENSERVER_PASS="$1"
LOGDIR=${LOGDIR:-"/opt/stack/devstack_logs"}
# Include onexit commands
. $SCRIPT_DIR/on_exit.sh

# xapi functions
. $COMM_DIR/functions

# Source params - override xenrc params in your localrc to suite your taste
source $CONF_DIR/xenrc

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
    echo "Stage is not properly set up!"
    exit 1
fi

if [ ! -d "$STAGING_DIR/opt/stack" ]; then
    echo "stack folder isn't exist yet"
    exit -1
fi

rm -f $STAGING_DIR/opt/stack/local.conf
XENSERVER_IP=$(xe host-list params=address minimal=true)
cat << LOCALCONF_CONTENT_ENDS_HERE > local.conf
# ``local.conf`` is a user-maintained settings file that is sourced from ``stackrc``.
# This gives it the ability to override any variables set in ``stackrc``.
# The ``localrc`` section replaces the old ``localrc`` configuration file.
# Note that if ``localrc`` is present it will be used in favor of this section.
# --------------------------------
[[local|localrc]]

enable_plugin os-xenapi https://github.com/openstack/os-xenapi.git

# Passwords
MYSQL_PASSWORD=citrix
SERVICE_TOKEN=citrix
ADMIN_PASSWORD=citrix
SERVICE_PASSWORD=citrix
RABBIT_PASSWORD=citrix
GUEST_PASSWORD=citrix
XENAPI_PASSWORD="$XENSERVER_PASS"
SWIFT_HASH="66a3d6b56c1f479c8b4e70ab5c2000f5"

# Nice short names, so we could export an XVA
VM_BRIDGE_OR_NET_NAME="osvmnet"
PUB_BRIDGE_OR_NET_NAME="ospubnet"
XEN_INT_BRIDGE_OR_NET_NAME="osintnet"

# Do not use secure delete
CINDER_SECURE_DELETE=False

# Compute settings
VIRT_DRIVER=xenserver

# OpenStack VM settings
OSDOMU_VDI_GB=30
OSDOMU_MEM_MB=8192

TERMINATE_TIMEOUT=90
BUILD_TIMEOUT=600

# DevStack settings

LOGDIR=${LOGDIR}
LOGFILE=${LOGDIR}/stack.log

UBUNTU_INST_HTTP_HOSTNAME=archive.ubuntu.com
UBUNTU_INST_HTTP_DIRECTORY=/ubuntu

# Turn on verbosity (password input does not work otherwise)
VERBOSE=True

# XenAPI specific
XENAPI_CONNECTION_URL="http://$XENSERVER_IP"
VNCSERVER_PROXYCLIENT_ADDRESS="$XENSERVER_IP"

# Neutron specific part
ENABLED_SERVICES+=neutron,q-domua
Q_ML2_PLUGIN_MECHANISM_DRIVERS=openvswitch

Q_ML2_PLUGIN_TYPE_DRIVERS=vlan,flat
ENABLE_TENANT_TUNNELS=False
ENABLE_TENANT_VLANS=True
Q_ML2_TENANT_NETWORK_TYPE=vlan
ML2_VLAN_RANGES="physnet1:1100:1200"

PUB_IP=172.24.4.1
SUBNETPOOL_PREFIX_V4=192.168.10.0/24
NETWORK_GATEWAY=192.168.10.1

VLAN_INTERFACE=eth1
PUBLIC_INTERFACE=eth2

# Nova user specific configuration
# --------------------------------
[[post-config|\\\$NOVA_CONF]]
[DEFAULT]
disk_allocation_ratio = 2.0

LOCALCONF_CONTENT_ENDS_HERE

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

# Configure the hostname
echo $DEV_STACK_DOMU_NAME > $STAGING_DIR/etc/hostname

# Gracefully cp only if source file/dir exists
function cp_it {
    if [ -e $1 ] || [ -d $1 ]; then
        cp -pRL $1 $2
    fi
}

# Copy over your ssh keys and env if desired
COPYENV=${COPYENV:-1}
if [ "$COPYENV" = "1" ]; then
    cp_it ~/.ssh $STAGING_DIR/opt/stack/.ssh
    cp_it ~/.ssh/id_rsa.pub $STAGING_DIR/opt/stack/.ssh/authorized_keys
    cp_it ~/.gitconfig $STAGING_DIR/opt/stack/.gitconfig
    cp_it ~/.vimrc $STAGING_DIR/opt/stack/.vimrc
    cp_it ~/.bashrc $STAGING_DIR/opt/stack/.bashrc
fi

# Configure run.sh
DOMU_STACK_DIR=/opt/stack
DOMU_DEV_STACK_DIR=$DOMU_STACK_DIR/devstack
DEVSTACK_SRC="https://github.com/openstack-dev/devstack"
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
cp_it local.conf $STAGING_DIR/opt/stack/local.conf
cp_it run.sh $STAGING_DIR/opt/stack/run.sh

xe vm-start vm="$DEV_STACK_DOMU_NAME"
