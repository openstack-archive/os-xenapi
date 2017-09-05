#!/bin/bash
set -eu

function print_usage_and_die
{
cat >&2 << EOF
usage: $0 XENSERVER XENSERVER_PASS PRIVKEY <optional arguments>

A simple script to use devstack to setup an OpenStack, and optionally
run tests on it. This script should be executed on an operator machine, and
it will execute commands through ssh on the remote XenServer specified.
You can use this script to install all-in-one or multihost OpenStack env.

positional arguments:
 XENSERVER          The address of the XenServer
 XENSERVER_PASS     The root password for the XenServer
 PRIVKEY            A passwordless private key to be used for installation.
                    This key will be copied over to the xenserver host, and will
                    be used for migration/resize tasks if multiple XenServers
                    used.  If '-' is passed, assume the key is provided by an agent

optional arguments:
 -t TEST_TYPE          Type of the tests to run. One of [none, exercise, smoke, full]
                       defaults to none
 -d DEVSTACK_SRC       It can be a local directory containing a local repository or
                       an URL pointing to a remote repository. This defaults to the
                       official devstack repository.
 -l LOG_FILE_DIRECTORY The directory in which to store the devstack logs on failure.
 -j JEOS_URL           An URL for an xva containing an exported minimal OS template
                       with the name jeos_template_for_ubuntu, to be used
                       as a starting point.
 -e JEOS_FILENAME      Save a JeOS xva to the given filename and quit. The exported
                       file could be re-used later by putting it to a webserver, and
                       specifying JEOS_URL.
 -s SUPP_PACK_URL      URL to a supplemental pack that will be installed on the host
                       before running any tests.  The host will not be rebooted after
                       installing the supplemental pack, so new kernels will not be
                       picked up.
 -o OS_XENAPI_SRC      It can be a local directory containing a local repository or
                       an URL pointing to a remote repository. This defaults to the
                       official os-xenapi repository.
 -w WAIT_TILL_LAUNCH   Set it to 1 if user want to pending on the installation until
                       it is done
 -a NODE_TYPE          OpenStack node type [all, compute]
 -m NODE_NAME          DomU name for installing OpenStack
 -i CONTROLLER_IP      IP address of controller node, must set it when installing compute node

flags:
 -f                 Force SR replacement. If your XenServer has an LVM type SR,
                    it will be destroyed and replaced with an ext SR.
                    WARNING: This will destroy your actual default SR !

 -n                 No devstack, just create the JEOS template that could be
                    exported to an xva using the -e option.

 -r                 Disable journaling if this flag is set. It will reduce disk IO, but
                    may lead to file system unstable after long time use

An example run:

  # Create a passwordless ssh key
  ssh-keygen -t rsa -N "" -f devstack_key.priv

  # Install devstack all-in-one (controller and compute node together)
  $0 XENSERVER mypassword devstack_key.priv
  or
  $0 XENSERVER mypassword devstack_key.priv -a all -m <node_name>

  # Install devstack compute node
  $0 XENSERVER mypassword devstack_key.priv -a compute -m <node_name> -i <controller_IP>

$@
EOF
exit 1
}

# Defaults for optional arguments
DEVSTACK_SRC=${DEVSTACK_SRC:-"https://github.com/openstack-dev/devstack"}
OS_XENAPI_SRC=${OS_XENAPI_SRC:-"https://github.com/openstack/os-xenapi"}
TEST_TYPE="none"
FORCE_SR_REPLACEMENT="false"
EXIT_AFTER_JEOS_INSTALLATION=""
LOG_FILE_DIRECTORY=""
JEOS_URL=""
JEOS_FILENAME=""
SUPP_PACK_URL=""
LOGDIR="/opt/stack/devstack_logs"
WAIT_TILL_LAUNCH=1
JEOS_TEMP_NAME="jeos_template_for_ubuntu"
NODE_TYPE="all"
NODE_NAME=""
CONTROLLER_IP=""
DISABLE_JOURNALING="false"
DEFAULT_INSTALL_SRC="$(mktemp -d --suffix=install)"

# Get Positional arguments
set +u
XENSERVER="$1"
shift || print_usage_and_die "ERROR: XENSERVER not specified!"
XENSERVER_PASS="$1"
shift || print_usage_and_die "ERROR: XENSERVER_PASS not specified!"
PRIVKEY="$1"
shift || print_usage_and_die "ERROR: PRIVKEY not specified!"
set -u

# Number of options passed to this script
REMAINING_OPTIONS="$#"

# Get optional parameters
set +e
while getopts ":t:d:fnrl:j:e:o:s:w:a:i:m:" flag; do
    REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
    case "$flag" in
        t)
            TEST_TYPE="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            if ! [ "$TEST_TYPE" = "none" -o "$TEST_TYPE" = "smoke" -o "$TEST_TYPE" = "full" -o "$TEST_TYPE" = "exercise" ]; then
                print_usage_and_die "$TEST_TYPE - Invalid value for TEST_TYPE"
            fi
            ;;
        d)
            DEVSTACK_SRC="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        f)
            FORCE_SR_REPLACEMENT="true"
            ;;
        n)
            EXIT_AFTER_JEOS_INSTALLATION="true"
            ;;
        l)
            LOG_FILE_DIRECTORY="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        j)
            JEOS_URL="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        e)
            JEOS_FILENAME="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        s)
            SUPP_PACK_URL="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        o)
            OS_XENAPI_SRC="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        w)
            WAIT_TILL_LAUNCH="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        a)
            NODE_TYPE="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            if [ $NODE_TYPE != "all" ] && [ $NODE_TYPE != "compute" ]; then
                print_usage_and_die "$NODE_TYPE - Invalid value for NODE_TYPE"
            fi
            ;;
        i)
            CONTROLLER_IP="$OPTARG"
            REMAINING_OPTIONS=$(expr "$REMAINING_OPTIONS" - 1)
            ;;
        m)
            NODE_NAME="$OPTARG"
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
if [ "$TEST_TYPE" != "none" ] && [ $WAIT_TILL_LAUNCH -ne 1 ]; then
    echo "WARNING: You can't perform a test even before the insallation done, force set WAIT_TILL_LAUNCH to 1"
    WAIT_TILL_LAUNCH=1
fi

if [ "$TEST_TYPE" != "none" ] && [ "$EXIT_AFTER_JEOS_INSTALLATION" = "true" ]; then
    print_usage_and_die "ERROR: You can't perform a test without a devstack invironment, exit"
fi

# Make sure that all options processed
if [ "0" != "$REMAINING_OPTIONS" ]; then
    print_usage_and_die "ERROR: some arguments were not recognised!"
fi

# Give DomU a default name when installing all-in-one
if [[ "$NODE_TYPE" = "all" && "$NODE_NAME" = "" ]]; then
    NODE_NAME="DevStackOSDomU"
fi

# Check CONTROLLER_IP is set when installing a compute node
if [ "$NODE_TYPE" = "compute" ]; then
    if [[ "$CONTROLLER_IP" = "" || "$NODE_NAME" = "" ]]; then
        print_usage_and_die "ERROR: CONTROLLER_IP or NODE_NAME not specified when installing compute node!"
    fi
    if [ "$TEST_TYPE" != "none" ]; then
        print_usage_and_die "ERROR: Cannot do test on compute node!"
    fi
fi

# Set up internal variables
_SSH_OPTIONS="\
    -o BatchMode=yes \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null"

if [ "$PRIVKEY" != "-" ]; then
  _SSH_OPTIONS="$_SSH_OPTIONS -i $PRIVKEY"
fi

# Print out summary
cat << EOF
XENSERVER:      $XENSERVER
XENSERVER_PASS: $XENSERVER_PASS
PRIVKEY:        $PRIVKEY
TEST_TYPE:      $TEST_TYPE
NODE_TYPE:      $NODE_TYPE
NODE_NAME:      $NODE_NAME
CONTROLLER_IP:  $CONTROLLER_IP
DEVSTACK_SRC:   $DEVSTACK_SRC
OS_XENAPI_SRC:  $OS_XENAPI_SRC


FORCE_SR_REPLACEMENT: $FORCE_SR_REPLACEMENT
JEOS_URL:             ${JEOS_URL:-template will not be imported}
JEOS_FILENAME:        ${JEOS_FILENAME:-not exporting JeOS}
SUPP_PACK_URL:        ${SUPP_PACK_URL:-no supplemental pack}
EOF

# Helper function
function on_xenserver() {
    ssh $_SSH_OPTIONS "root@$XENSERVER" bash -s --
}

function assert_tool_exists() {
    local tool_name

    tool_name="$1"

    if ! which "$tool_name" >/dev/null; then
        echo "ERROR: $tool_name is required for this script, please install it on your system! " >&2
        exit 1
    fi
}

if [ "$PRIVKEY" != "-" ]; then
    echo "Setup ssh keys on XenServer..."
    tmp_dir="$(mktemp -d --suffix=OpenStack)"
    echo "Use $tmp_dir for public/private keys..."
    cp $PRIVKEY "$tmp_dir/devstack"
    ssh-keygen -y -f $PRIVKEY > "$tmp_dir/devstack.pub"
    assert_tool_exists sshpass
    echo "Setup public key to XenServer..."
    DEVSTACK_PUB=$(cat $tmp_dir/devstack.pub)
    sshpass -p "$XENSERVER_PASS" \
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        root@$XENSERVER "echo $DEVSTACK_PUB >> ~/.ssh/authorized_keys"
    scp $_SSH_OPTIONS $PRIVKEY "root@$XENSERVER:.ssh/id_rsa"
    scp $_SSH_OPTIONS $tmp_dir/devstack.pub "root@$XENSERVER:.ssh/id_rsa.pub"
    rm -rf "$tmp_dir"
    unset tmp_dir
    echo "OK"
fi

DEFAULT_SR_ID=$(on_xenserver <<EOF
xe pool-list params=default-SR minimal=true
EOF
)
TMP_TEMPLATE_DIR=/var/run/sr-mount/$DEFAULT_SR_ID/devstack_template

if [ ! -z "$JEOS_FILENAME" ]; then
    echo -n "Exporting JeOS template..."
    echo "template will save to $TMP_TEMPLATE_DIR"

    on_xenserver << END_OF_EXPORT_COMMANDS
set -eu

mkdir -p $TMP_TEMPLATE_DIR

JEOS_TEMPLATE="\$(. "$COMM_DIR/functions" &&  get_template $JEOS_TEMP_NAME $(get_current_host_uuid))
if [ JEOS_TEMPLATE==*,* ]; then
    JEOS_TEMPLATE=${JEOS_TEMPLATE##*,}
fi

if [ -z "\$JEOS_TEMPLATE" ]; then
    echo "FATAL: $JEOS_TEMP_NAME not found"
    exit 1
fi
rm -rf $TMP_TEMPLATE_DIR/jeos-for-devstack.xva
xe template-export template-uuid="\$JEOS_TEMPLATE" filename="\$TMP_TEMPLATE_DIR/jeos-for-devstack.xva" compress=true
END_OF_EXPORT_COMMANDS
    echo "OK"

    echo -n "Copy exported template to local file..."
    if scp -3 $_SSH_OPTIONS "root@$XENSERVER:$TMP_TEMPLATE_DIR/jeos-for-devstack.xva" "$JEOS_FILENAME"; then
        echo "OK"
        RETURN_CODE=0
    else
        echo "FAILED"
        RETURN_CODE=1
    fi
    echo "Cleanup: delete exported template from XenServer"
    on_xenserver << END_OF_CLEANUP
set -eu

rm -rf $TMP_TEMPLATE_DIR
END_OF_CLEANUP
    echo "JeOS export done, exiting."
    exit $RETURN_CODE
fi

function copy_logs_on_failure() {
    set +e
    $@
    EXIT_CODE=$?
    set -e
    if [ $EXIT_CODE -ne 0 ]; then
        copy_logs
        exit $EXIT_CODE
    fi
}

function copy_logs() {
    if [ -n "$LOG_FILE_DIRECTORY" ]; then
        on_xenserver << END_OF_XENSERVER_COMMANDS
set -xu

mkdir -p /root/artifacts
GUEST_IP=\$(. "$COMM_DIR/functions" && find_ip_by_name $NODE_NAME 0)
if [ -n \$GUEST_IP ]; then
ssh -q \
    -o Batchmode=yes \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    stack@\$GUEST_IP "tar --ignore-failed-read -czf - ${LOGDIR}/* /opt/stack/tempest/*.xml" > \
    /root/artifacts/domU.tgz < /dev/null || true
fi
tar --ignore-failed-read -czf /root/artifacts/dom0.tgz /var/log/messages* /var/log/xensource* /var/log/SM* || true
END_OF_XENSERVER_COMMANDS

        mkdir -p $LOG_FILE_DIRECTORY
        scp $_SSH_OPTIONS $XENSERVER:artifacts/* $LOG_FILE_DIRECTORY
        tar -xzf $LOG_FILE_DIRECTORY/domU.tgz opt/stack/tempest/tempest-full.xml -O \
           > $LOG_FILE_DIRECTORY/tempest-full.xml || true
    fi
}

echo -n "Generate id_rsa.pub..."
echo "ssh-keygen -y -f .ssh/id_rsa > .ssh/id_rsa.pub" | on_xenserver
echo "OK"

echo -n "Verify that XenServer can log in to itself..."
if echo "ssh -o StrictHostKeyChecking=no $XENSERVER true" | on_xenserver; then
    echo "OK"
else
    echo ""
    echo ""
    echo "ERROR: XenServer couldn't authenticate to itself. This might"
    echo "be caused by having a key originally installed on XenServer"
    echo "consider using the -w parameter to wipe all your ssh settings"
    echo "on XenServer."
    exit 1
fi

echo "OK"

if [ -n "$SUPP_PACK_URL" ]; then
    echo -n "Applying supplemental pack"
    on_xenserver <<SUPP_PACK
set -eu
wget -qO /root/supp_pack_for_devstack.iso $SUPP_PACK_URL
xe-install-supplemental-pack /root/supp_pack_for_devstack.iso
reboot
SUPP_PACK
    echo -n "Rebooted host; waiting 10 minutes"
    sleep 10m
fi

if [ -n "$JEOS_URL" ]; then
    echo "(re-)importing JeOS template"
    on_xenserver << END_OF_JEOS_IMPORT
set -eu

mkdir -p $TMP_TEMPLATE_DIR

JEOS_TEMPLATE="\$(. "$COMM_DIR/functions" &&  get_template $JEOS_TEMP_NAME $(get_current_host_uuid))

if [ -n "\$JEOS_TEMPLATE" ]; then
    echo "  $JEOS_TEMP_NAME already exist, uninstalling"
    IFS=','
    for i in "\${JEOS_TEMPLATE[@]}"; do
        xe template-uninstall template-uuid="\$i" force=true > /dev/null
    done
fi

rm -f $TMP_TEMPLATE_DIR/jeos-for-devstack.xva
echo "  downloading $JEOS_URL to $TMP_TEMPLATE_DIR/jeos-for-devstack.xva"
wget -qO $TMP_TEMPLATE_DIR/jeos-for-devstack.xva "$JEOS_URL"
echo "  importing $TMP_TEMPLATE_DIR/jeos-for-devstack.xva"
xe vm-import filename=$TMP_TEMPLATE_DIR/jeos-for-devstack.xva
rm -rf $TMP_TEMPLATE_DIR
echo "  verify template imported"
JEOS_TEMPLATE="\$(. "$COMM_DIR/functions" &&  get_template $JEOS_TEMP_NAME $(get_current_host_uuid))
if [ -z "\$JEOS_TEMPLATE" ]; then
    echo "FATAL: template $JEOS_TEMP_NAME does not exist after import."
    exit 1
fi

END_OF_JEOS_IMPORT
    echo "OK"
fi

# Got install repositories.
# If input repository is an URL, for os-xenapi, it is only needed on xenserver,
# so we will download it and move it to xenserver when needed; for devstack, it
# is needed on DomU, so we configure a service on DomU and download it after
# DomU first bootup.
if [ -d $DEVSTACK_SRC ]; then
    # Local repository for devstack exist, copy it to default directory for
    # unified treatment
    cp -rf $DEVSTACK_SRC $DEFAULT_INSTALL_SRC
    DEVSTACK_SRC=$DEFAULT_INSTALL_SRC/devstack
fi
if [ ! -d $OS_XENAPI_SRC ]; then
    # Local repository for os-xenapi does not exist, OS_XENAPI_SRC must be a git
    # URL. Download it to default directory
    git clone $OS_XENAPI_SRC $DEFAULT_INSTALL_SRC/os-xenapi
else
    # Local repository for os-xenapi exists, copy it to default directory
    # unified treatment
    cp -rf $OS_XENAPI_SRC $DEFAULT_INSTALL_SRC
fi

TMPDIR=$(echo "mktemp -d" | on_xenserver)

set +u
DOM0_OPT_DIR=$TMPDIR/domU
ssh $_SSH_OPTIONS root@$XENSERVER "[ -d $DOM0_OPT_DIR ] && echo ok || mkdir -p $DOM0_OPT_DIR"
tar -zcvf local_res.tar.gz $DEFAULT_INSTALL_SRC
scp $_SSH_OPTIONS local_res.tar.gz root@$XENSERVER:$DOM0_OPT_DIR
rm -f local_res.tar.gz
DOM0_OS_API_DIR=$DOM0_OPT_DIR/os-xenapi
if [ -d $DEVSTACK_SRC ]; then
    DEVSTACK_SRC=$DOM0_OPT_DIR/devstack
fi
copy_logs_on_failure on_xenserver << END_OF_XENSERVER_COMMANDS

    cd $DOM0_OPT_DIR
    tar -zxvf local_res.tar.gz
    # remove root flag
    DEFAULT_INSTALL_SRC=${DEFAULT_INSTALL_SRC#*/}
    mv \$DEFAULT_INSTALL_SRC/* ./
    DOM0_TOOL_DIR="$DOM0_OS_API_DIR/tools"
    DOM0_INSTALL_DIR="\$DOM0_TOOL_DIR/install"
    cd \$DOM0_INSTALL_DIR

    # override items in xenrc
    sed -i "s/DevStackOSDomU/$NODE_NAME/g" \$DOM0_INSTALL_DIR/conf/xenrc

    # prepare local.conf
cat << LOCALCONF_CONTENT_ENDS_HERE > local.conf
# ``local.conf`` is a user-maintained settings file that is sourced from ``stackrc``.
# This gives it the ability to override any variables set in ``stackrc``.
# The ``localrc`` section replaces the old ``localrc`` configuration file.
# Note that if ``localrc`` is present it will be used in favor of this section.
# --------------------------------
[[local|localrc]]

enable_plugin os-xenapi https://github.com/openstack/os-xenapi.git

# workaround for bug/1709594
CELLSV2_SETUP=singleconductor

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

# Do not use secure delete
CINDER_SECURE_DELETE=False

# Compute settings
VIRT_DRIVER=xenserver

# Tempest settings
TERMINATE_TIMEOUT=90
BUILD_TIMEOUT=600

# DevStack settings
LOGDIR=${LOGDIR}
LOGFILE=${LOGDIR}/stack.log

# Turn on verbosity (password input does not work otherwise)
VERBOSE=True

# XenAPI specific
XENAPI_CONNECTION_URL="http://$XENSERVER"
VNCSERVER_PROXYCLIENT_ADDRESS="$XENSERVER"

# Neutron specific part
Q_ML2_PLUGIN_MECHANISM_DRIVERS=openvswitch
Q_ML2_PLUGIN_TYPE_DRIVERS=vxlan,flat
Q_ML2_TENANT_NETWORK_TYPE=vxlan

VLAN_INTERFACE=eth1
PUBLIC_INTERFACE=eth2

LOCALCONF_CONTENT_ENDS_HERE

if [ "$NODE_TYPE" = "all" ]; then
cat << LOCALCONF_CONTENT_ENDS_HERE >> local.conf
ENABLED_SERVICES+=,neutron,q-domua
LOCALCONF_CONTENT_ENDS_HERE
else
cat << LOCALCONF_CONTENT_ENDS_HERE >> local.conf
ENABLED_SERVICES=neutron,q-agt,q-domua,n-cpu,placement-client,dstat
SERVICE_HOST=$CONTROLLER_IP
MYSQL_HOST=$CONTROLLER_IP
GLANCE_HOST=$CONTROLLER_IP
RABBIT_HOST=$CONTROLLER_IP
KEYSTONE_AUTH_HOST=$CONTROLLER_IP
LOCALCONF_CONTENT_ENDS_HERE
fi

cat << LOCALCONF_CONTENT_ENDS_HERE >> local.conf
# Nova user specific configuration
# --------------------------------
[[post-config|\\\$NOVA_CONF]]
[DEFAULT]
disk_allocation_ratio = 2.0

LOCALCONF_CONTENT_ENDS_HERE

# begin installation process
cd \$DOM0_TOOL_DIR
OPTARGS=""
if [ $FORCE_SR_REPLACEMENT = 'true' ]; then
  OPTARGS="\$OPTARGS -f"
fi
if [ $DISABLE_JOURNALING = 'true' ]; then
  OPTARGS="\$OPTARGS -r"
fi
./install_on_xen_host.sh -d $DEVSTACK_SRC -l $LOGDIR -w $WAIT_TILL_LAUNCH \$OPTARGS

END_OF_XENSERVER_COMMANDS

on_xenserver << END_OF_RM_TMPDIR

#delete install dir
rm $TMPDIR -rf
END_OF_RM_TMPDIR

# Sync compute node info in controller node
if [ "$NODE_TYPE" = "compute" ]; then
    set +x
    echo "################################################################################"
    echo ""
    echo "Sync compute node info in controller node!"

    ssh $_SSH_OPTIONS stack@$CONTROLLER_IP bash -s -- << END_OF_SYNC_COMPUTE_COMMANDS
set -exu
cd /opt/stack/devstack/tools/
. discover_hosts.sh
END_OF_SYNC_COMPUTE_COMMANDS
fi

if [ "$TEST_TYPE" == "none" ]; then
    exit 0
fi

# Run tests
DOM0_FUNCTION_DIR="$DOM0_OS_API_DIR/install/common"
copy_logs_on_failure on_xenserver << END_OF_XENSERVER_COMMANDS

set -exu

GUEST_IP=\$(. $DOM0_FUNCTION_DIR/functions && find_ip_by_name $NODE_NAME 0)
ssh -q \
    -o Batchmode=yes \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "stack@\$GUEST_IP" bash -s -- << END_OF_DEVSTACK_COMMANDS
set -exu

cd /opt/stack/tempest
if [ "$TEST_TYPE" == "exercise" ]; then
    tox -eall tempest.scenario.test_server_basic_ops
elif [ "$TEST_TYPE" == "smoke" ]; then
    #./run_tests.sh -s -N
    tox -esmoke
elif [ "$TEST_TYPE" == "full" ]; then
    #nosetests -sv --with-xunit --xunit-file=tempest-full.xml tempest/api tempest/scenario tempest/thirdparty tempest/cli
    tox -efull
fi

END_OF_DEVSTACK_COMMANDS

END_OF_XENSERVER_COMMANDS

rm -rf $DEFAULT_INSTALL_SRC

copy_logs
