#!/bin/bash

# This script is run by install_on_xen_host.sh
#
# It modifies the ubuntu image created by install_on_xen_host.sh
# and previously moodified by prepare_guest_template.sh
#
# This script is responsible for:
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

XENSERVER_PASS="$1"
shift

# Defaults for optional arguments
DEVSTACK_SRC=${DEVSTACK_SRC:-"https://github.com/openstack-dev/devstack"}
LOGDIR="/opt/stack/devstack_logs"

# Number of options passed to this script
REMAINING_OPTIONS="$#"
# Get optional parameters
set +e
while getopts ":d:l:" flag; do
    REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
    case "$flag" in
        d)
            DEVSTACK_SRC="$DEVSTACK_SRC"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        l)
            LOGDIR="$LOGDIR"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
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
    echo "You should prepare a local.conf and put it under $TOP_DIR"
    exit 1
fi

cp_it local.conf $STAGING_DIR/opt/stack/local.conf
cp_it run.sh $STAGING_DIR/opt/stack/run.sh
