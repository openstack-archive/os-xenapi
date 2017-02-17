#!/bin/bash
#
# Copyright 2013 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

MODE=$1
PHASE=$2

OS_XENAPI_DIR=$DEST/os-xenapi
XS_DOM0_IPTABLES_CHAIN="XenServerDevstack"

OVS_PORT=${OVS_PORT:-"6640"}
VXLAN_PORT=${VXLAN_PORT:-"4789"}


function get_dom0_ssh {
    local dom0_ip
    dom0_ip=$(echo "$XENAPI_CONNECTION_URL" | cut -d "/" -f 3)

    local ssh_dom0
    ssh_dom0="sudo -u $DOMZERO_USER ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$dom0_ip"
    echo $ssh_dom0
    return 0
}

# Install Nova and Neutron Dom0 plugins
function install_dom0_plugins {
    local ssh_dom0
    ssh_dom0=$(get_dom0_ssh)

    local dom0_func
    dom0_func=`cat $OS_XENAPI_DIR/devstack/dom0_functions`
    local dom0_plugin_dir
    dom0_plugin_dir=`$ssh_dom0 "$dom0_func; set -eux; dom0_plugin_location"`

    # Get the path that os-xenapi is installed or the path that nova source code resides
    # Note: This aims to be compatible whenever dom0 plugin is in os-xenapi repo or in nova repo
    local plugin_dir
    plugin_dir=$(sudo -H pip show os-xenapi |grep "Location:"|cut -d " " -f 2-)
    if [ -z "$plugin_dir" ]; then
        pip_install_gr xenapi
        plugin_dir=$DEST/nova
        tar -czf - -C $plugin_dir/plugins/xenserver/xenapi/etc/xapi.d/plugins/ ./ |
            $ssh_dom0 "tar -xzf - -C $dom0_plugin_dir && chmod a+x $dom0_plugin_dir/*"
    else
        # TODO(huanxie): delete "pip_install_gr xenapi" when neutron changed to use os-xenapi
        pip_install_gr xenapi
        tar -czf - -C $plugin_dir/os_xenapi/dom0/etc/xapi.d/plugins/ ./ |
            $ssh_dom0 "tar -xzf - -C $dom0_plugin_dir && chmod a+x $dom0_plugin_dir/*"
    fi

    # TODO(huanxie): delete below when neutron's xs dom0 plugin moved to os-xenapi
    # install neutron dom0 plugins as it's not moved to os-xenapi
    tar -czf - -C $NEUTRON_DIR/neutron/plugins/ml2/drivers/openvswitch/agent/xenapi/etc/xapi.d/plugins/ ./ |
        $ssh_dom0 "tar -xzf - -C $dom0_plugin_dir && chmod a+x $dom0_plugin_dir/*"
}

# Config iptables in Dom0
function config_dom0_iptables {
    local ssh_dom0=$(get_dom0_ssh)

    # Remove restriction on linux bridge in Dom0 since neutron is default
    $ssh_dom0 "rm -f /etc/modprobe.d/blacklist-bridge*"

    # Save errexit setting
    _ERREXIT_XENSERVER=$(set +o | grep errexit)
    set +o errexit

    # Check Dom0 internal chain for Neutron, add if not exist
    $ssh_dom0 "iptables -t filter -L $XS_DOM0_IPTABLES_CHAIN"
    local chain_result=$?
    if [ "$chain_result" != "0" ]; then
        $ssh_dom0 "iptables -t filter --new $XS_DOM0_IPTABLES_CHAIN"
        $ssh_dom0 "iptables -t filter -I INPUT -j $XS_DOM0_IPTABLES_CHAIN"
    fi

    # Check iptables for remote ovsdb connection, add if not exist
    $ssh_dom0 "iptables -t filter -C $XS_DOM0_IPTABLES_CHAIN -p tcp -m tcp --dport $OVS_PORT -j ACCEPT"
    local remote_conn_result=$?
    if [ "$remote_conn_result" != "0" ]; then
        $ssh_dom0 "iptables -t filter -I $XS_DOM0_IPTABLES_CHAIN -p tcp --dport $OVS_PORT -j ACCEPT"
    fi

    # Check iptables for VxLAN, add if not exist
    $ssh_dom0 "iptables -t filter -C $XS_DOM0_IPTABLES_CHAIN -p udp -m multiport --dports $VXLAN_PORT -j ACCEPT"
    local vxlan_result=$?
    if [ "$vxlan_result" != "0" ]; then
        $ssh_dom0 "iptables -t filter -I $XS_DOM0_IPTABLES_CHAIN -p udp -m multiport --dport $VXLAN_PORT -j ACCEPT"
    fi

    # Restore errexit setting
    $_ERREXIT_XENSERVER
}

# Configure ovs agent for compute node, i.e. q-domua
function config_ovs_agent {
    # TODO(huan): remove below line when devstack is cleanup with dom0
    sudo rm -f "$NEUTRON_CORE_PLUGIN_CONF.domU"

    # Make a copy of our config for domU
    sudo cp $NEUTRON_CORE_PLUGIN_CONF "$NEUTRON_CORE_PLUGIN_CONF.domU"

    # Change domU's config file to STACK_USER
    sudo chown $STACK_USER:$STACK_USER $NEUTRON_CORE_PLUGIN_CONF.domU

    # Configure xen configuration for neutron rootwrap.conf
    iniset $NEUTRON_ROOTWRAP_CONF_FILE xenapi xenapi_connection_url "$XENAPI_CONNECTION_URL"
    iniset $NEUTRON_ROOTWRAP_CONF_FILE xenapi xenapi_connection_username "$XENAPI_USER"
    iniset $NEUTRON_ROOTWRAP_CONF_FILE xenapi xenapi_connection_password "$XENAPI_PASSWORD"

    # Configure q-domua, use Dom0's hostname and concat suffix
    local ssh_dom0=$(get_dom0_ssh)
    local dom0_hostname=`$ssh_dom0 "hostname"`
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU DEFAULT host "$dom0_hostname-nova"

    # TODO(huanxie): XenServer supports rootwrap daemon now, reconfigure below
    # Under XS/XCP, the ovs agent needs to target the dom0
    # integration bridge.  This is enabled by using a root wrapper
    # that executes commands on dom0 via a XenAPI plugin.
    # XenAPI does not support daemon rootwrap now, so set root_helper_daemon empty
    # Deal with Dom0's L2 Agent:
    local rootwrap_dom0_cmd="$NEUTRON_BIN_DIR/neutron-rootwrap-xen-dom0 $NEUTRON_ROOTWRAP_CONF_FILE"
    iniset "$NEUTRON_CORE_PLUGIN_CONF.domU" agent root_helper "$rootwrap_dom0_cmd"
    iniset "$NEUTRON_CORE_PLUGIN_CONF.domU" agent root_helper_daemon ""

    # TODO(huanxie): XenServer supports minimized poll now, reconfigure below
    # Disable minimize polling, so that it can always detect OVS and Port changes
    # This is a problem of xenserver + neutron, bug has been reported
    # https://bugs.launchpad.net/neutron/+bug/1495423
    iniset "$NEUTRON_CORE_PLUGIN_CONF.domU" agent minimize_polling False

    # Set integration bridge for ovs-agent in compute node (q-domua)
    iniset "$NEUTRON_CORE_PLUGIN_CONF.domU" ovs integration_bridge $OVS_BRIDGE

    # Set OVS native interface for ovs-agent in compute node (q-domua)
    local dom0_ip=$(echo "$XENAPI_CONNECTION_URL" | cut -d "/" -f 3)
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs ovsdb_connection tcp:$dom0_ip:$OVS_PORT
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs of_listen_address $HOST_IP

    # Clean bridge mapping as it's copied from $NEUTRON_CORE_PLUGIN_CONF (q-agt)
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs bridge_mappings ""

    if [[ "$ENABLE_TENANT_VLANS" == "True" ]]; then
        # Create a bridge "br-$VLAN_INTERFACE" and add port
        _neutron_ovs_base_add_bridge "br-$VLAN_INTERFACE"
        sudo ovs-vsctl -- --may-exist add-port "br-$VLAN_INTERFACE" $VLAN_INTERFACE
        _move_neutron_addresses_route "br-$VLAN_INTERFACE" "$VLAN_INTERFACE" False True "inet"

        # Set bridge mapping for q-domua which is for compute node
        iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs bridge_mappings "physnet1:$FLAT_NETWORK_BRIDGE"

        # Set bridge mappings for q-agt as we have an extra bridge mapping physnet1 for domU and dom0
        iniset $NEUTRON_CORE_PLUGIN_CONF ovs bridge_mappings "physnet1:br-$VLAN_INTERFACE,$PHYSICAL_NETWORK:$PUBLIC_BRIDGE"
    fi

    if [[ "$OVS_ENABLE_TUNNELING" == "True" ]]; then
        # Set tunnel ip for openvswitch agent in compute node (q-domua).
        # All q-domua's OVS commands are executed in Dom0 as Xen has the privileged and unprivileged domain,
        # the tunnel is established between Dom0 and DomU(where devstack runs),
        # thus we need to change the local_ip in q-domua that is used for Dom0
        iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs local_ip $dom0_ip
    fi
}

function config_nova_compute {
    iniset $NOVA_CONF xenserver vif_driver nova.virt.xenapi.vif.XenAPIOpenVswitchDriver
    iniset $NOVA_CONF xenserver ovs_integration_bridge $OVS_BRIDGE
    iniset $NOVA_CONF DEFAULT firewall_driver nova.virt.firewall.NoopFirewallDriver
    # Configure nova-compute, use Dom0's hostname and concat suffix
    local ssh_dom0=$(get_dom0_ssh)
    local dom0_hostname=`$ssh_dom0 "hostname"`
    iniset $NOVA_CONF DEFAULT host "$dom0_hostname-nova"
}

# Start neutron-openvswitch-agent for Dom0 (q-domua)
function start_ovs_agent {
    # TODO(huanxie): neutron-legacy is deprecated, checking is_neutron_legacy_enabled
    # can make our code more compatible with devstack future changes, see link
    # https://github.com/openstack-dev/devstack/blob/master/lib/neutron-legacy#L62
    if is_neutron_legacy_enabled; then
        # TODO(huanxie): delete below when https://review.openstack.org/#/c/435224/ merged
        stop_process q-domua

        # For XenServer, start an agent for the dom0 openvswitch (q-domua)
        run_process q-domua "$AGENT_BINARY --config-file $NEUTRON_CONF --config-file $NEUTRON_CORE_PLUGIN_CONF.domU"
    else
        local config_file="--config-file $NEUTRON_CONF --config-file $NEUTRON_CORE_PLUGIN_CONF.domU"
        run_process neutron-agent-dom0 "$NEUTRON_BIN_DIR/$NEUTRON_AGENT_BINARY $config_file"
    fi
}

# Stop neutron-openvswitch-agent for Dom0 (q-domua)
function stop_ovs_agent {
    if is_neutron_legacy_enabled; then
        stop_process q-domua
    else
        stop_process neutron-agent-dom0
    fi
}

if [[ "$MODE" == "stack" ]]; then
    case "$PHASE" in
        pre-install)
            # Called after system (OS) setup is complete and before project source is installed
            ;;
        install)
            # Called after the layer 1 and 2 projects source and their dependencies have been installed
            install_dom0_plugins
            config_dom0_iptables
            # set image variables
            DEFAULT_IMAGE_NAME="cirros-${CIRROS_VERSION}-${CIRROS_ARCH}-disk"
            DEFAULT_IMAGE_FILE_NAME="cirros-${CIRROS_VERSION}-${CIRROS_ARCH}-disk.vhd.tgz"
            IMAGE_URLS="http://ca.downloads.xensource.com/OpenStack/cirros-${CIRROS_VERSION}-${CIRROS_ARCH}-disk.vhd.tgz"
            IMAGE_URLS+=",http://download.cirros-cloud.net/${CIRROS_VERSION}/cirros-${CIRROS_VERSION}-x86_64-uec.tar.gz"
            ;;
        post-config)
            # Called after the layer 1 and 2 services have been configured.
            # All configuration files for enabled services should exist at this point.
            # Configure XenServer neutron specific items for q-domua and n-cpu
            config_nova_compute
            config_ovs_agent
            ;;
        extra)
            # Called near the end after layer 1 and 2 services have been started
            start_ovs_agent
            ;;
        test-config)
            # Called at the end of devstack used to configure tempest
            # or any other test environments
            iniset $TEMPEST_CONFIG compute hypervisor_type XenServer
            iniset $TEMPEST_CONFIG compute volume_device_name xvdb
            iniset $TEMPEST_CONFIG scenario img_file $DEFAULT_IMAGE_FILE_NAME
            # TODO(huanxie) Maybe we can set some conf here for CI?
            ;;
    esac
elif [[ "$MODE" == "unstack" ]]; then
    # Called by unstack.sh before other services are shut down
    stop_ovs_agent
elif [[ "$MODE" == "clean" ]]; then
    # Called by clean.sh before other services are cleaned, but after unstack.sh has been called
    # TODO(huanxie)
    # clean the OVS bridge created in Dom0 and iptables rules?
    echo "mode is clean"
fi
