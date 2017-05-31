#!/bin/bash

set -o errexit
set -o nounset
set -o xtrace

export LC_ALL=C

# This directory
THIS_DIR=$(cd $(dirname "$0") && pwd)
COMM_DIR="$THIS_DIR/common"
CONF_DIR="$THIS_DIR/conf"

. $COMM_DIR/functions
# Source params - override xenrc params in your localrc to suit your taste
source $CONF_DIR/xenrc

XENSERVER_PASS="$1"

##
# begin install devstack process
##

# create template if needed
./create_ubuntu_template.sh
if [ -n "${EXIT_AFTER_JEOS_INSTALLATION:-}" ]; then
    echo "User requested to quit after JEOS installation"
    exit 0
fi
nohup  strace -f -p \$\$ >/tmp/strace.log 2>&1 &
# boot up a VM according to the template and config it to satisfy DevStack DomU requirement
./config_devstack_domu_vm.sh
# install DevStack on the VM
LOGDIR=${LOGDIR:-"/opt/stack/devstack_logs"}
LOGDIR=${LOGDIR} ./launch_devstack.sh $XENSERVER_PASS

# If we have copied our ssh credentials, use ssh to monitor while the installation runs
function ssh_no_check {
    ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "$@"
}

# Get hold of the Management IP of OpenStack VM
OS_VM_MANAGEMENT_ADDRESS=$MGT_IP
if [ $OS_VM_MANAGEMENT_ADDRESS == "dhcp" ]; then
    OS_VM_MANAGEMENT_ADDRESS=$(find_ip_by_name $DEV_STACK_DOMU_NAME $MGT_DEV_NR)
fi
WAIT_TILL_LAUNCH=${WAIT_TILL_LAUNCH:-0}
COPYENV=${COPYENV:-1}

echo "DomU ip is $OS_VM_MANAGEMENT_ADDRESS, log dir is $LOGDIR"
if [ "$WAIT_TILL_LAUNCH" = "1" ]  && [ -e ~/.ssh/id_rsa.pub  ] && [ "$COPYENV" = "1" ]; then
    set +x

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

    set -x
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
