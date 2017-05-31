#!/bin/bash

set -o errexit
set -o nounset
set -o xtrace

export LC_ALL=C

# This directory
THIS_DIR=$(cd $(dirname "$0") && pwd)
INSTALL_DIR="$THIS_DIR/install"

COMM_DIR="$INSTALL_DIR/common"
CONF_DIR="$INSTALL_DIR/conf"
DEV_STACK_DIR="$INSTALL_DIR/devstack"

. $COMM_DIR/functions
# Source params - override xenrc params in your localrc to suit your taste
source $CONF_DIR/xenrc

function print_usage_and_die
{
cat >&2 << EOF
usage: $0 <optional arguments>

A simple script to use devstack to setup an OpenStack. This script should be
executed on a xenserver host.

optional arguments:
 -d DEVSTACK_SRC       An URL pointing to a tar.gz snapshot of devstack. This
                       defaults to the official devstack repository.  Can also be a local
                       file location.
 -l LOG_FILE_DIRECTORY The directory in which to store the devstack logs on failure.
 -w WAIT_TILL_LAUNCH   Set it to 1 if user want to pending on the installation until
                       it is done

An example run:

  # Install devstack
  $0 mypassword

$@
EOF
exit 1
}

# Defaults for optional arguments
DEVSTACK_SRC=${DEVSTACK_SRC:-"https://github.com/openstack-dev/devstack"}
LOGDIR="/opt/stack/devstack_logs"
WAIT_TILL_LAUNCH=1

# Number of options passed to this script
REMAINING_OPTIONS="$#"

# Get optional parameters
set +e
while getopts ":d:l:w:" flag; do
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
        w)
            WAIT_TILL_LAUNCH="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        \?)
            print_usage_and_die "Invalid option -$OPTARG"
            exit 1
            ;;
    esac
done
set -e

# Make sure that all options processed
if [ "0" != "$REMAINING_OPTIONS" ]; then
    print_usage_and_die "ERROR: some arguments were not recognised!"
fi

##
# begin install devstack process
##

# create template if needed
$INSTALL_DIR/create_ubuntu_template.sh
if [ -n "${EXIT_AFTER_JEOS_INSTALLATION:-}" ]; then
    echo "User requested to quit after JEOS installation"
    exit 0
fi

# install DevStack on the VM
$DEV_STACK_DIR/install_devstack.sh -d $DEVSTACK_SRC -l $LOGDIR

#start openstack domU VM
xe vm-start vm="$DEV_STACK_DOMU_NAME"

# If we have copied our ssh credentials, use ssh to monitor while the installation runs
function ssh_no_check {
    ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "$@"
}

# Get hold of the Management IP of OpenStack VM
OS_VM_MANAGEMENT_ADDRESS=$MGT_IP
if [ $OS_VM_MANAGEMENT_ADDRESS == "dhcp" ]; then
    OS_VM_MANAGEMENT_ADDRESS=$(find_ip_by_name $DEV_STACK_DOMU_NAME $MGT_DEV_NR)
fi

if [ "$WAIT_TILL_LAUNCH" = "1" ] && [ -e ~/.ssh/id_rsa.pub  ]; then
    echo "VM Launched - Waiting for run.sh"
    while ! ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "test -e /opt/stack/run_sh.pid"; do
        echo "VM Launched - Waiting for run.sh"
        sleep 10
    done
    echo -n "devstack service is running, waiting for stack.sh to start logging..."

    pid=`ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "cat /opt/stack/run_sh.pid"`
    if [ -n "$LOGDIR" ]; then
        while ! ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "test -e ${LOGDIR}/stack.log"; do
            echo -n "..."
            sleep 10
        done

        ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "tail --pid $pid -n +1 -f ${LOGDIR}/stack.log"
    else
        echo -n "LOGDIR not set; just waiting for process $pid to finish"
        ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS "wait $pid"
    fi
    # Fail if devstack did not succeed
    ssh_no_check -q stack@$OS_VM_MANAGEMENT_ADDRESS 'test -e /opt/stack/runsh.succeeded'
    set +x
    echo "################################################################################"
    echo ""
    echo "All Finished!"
    echo "You can visit the OpenStack Dashboard"
    echo "at http://$OS_VM_MANAGEMENT_ADDRESS, and contact other services at the usual ports."
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
    echo "at http://$OS_VM_MANAGEMENT_ADDRESS, and contact other services at the usual ports."
fi
