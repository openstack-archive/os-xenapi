#!/bin/bash
#
# Copyright 2016 Citrix Systems
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

DOM0_OVSDB_PORT=${DOM0_OVSDB_PORT:-"6640"}
DOM0_VXLAN_PORT=${DOM0_VXLAN_PORT:-"4789"}


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

    # We've moved the plugins from neutron/nova to os-xenapi, but in some stable branches the
    # plugins are still located in neutron (ocata and backforward branches) or nova (Newton
    # and backforward branches). In order to upport both stable and master branches, let's
    # check the existing for the potential plugin directories. And copy them if exist.
    local plugin_dir
    local need_install_xenapi=False
    # for neutron plugins
    plugin_dir=$DEST/neutron/neutron/plugins/ml2/drivers/openvswitch/agent/xenapi/etc/xapi.d/plugins/
    if [ -d $plugin_dir ]; then
        need_install_xenapi=True
        tar -czf - -C $plugin_dir ./ | $ssh_dom0 "tar -xzf - -C $dom0_plugin_dir"
    fi
    # for nova plugins
    plugin_dir=$DEST/nova/plugins/xenserver/xenapi/etc/xapi.d/plugins/
    if [ -d $plugin_dir ]; then
        need_install_xenapi=True
        tar -czf - -C $plugin_dir ./ | $ssh_dom0 "tar -xzf - -C $dom0_plugin_dir"
    fi

    if [ "$need_install_xenapi" = "True" ]; then
        # Either neutron or nova need XenAPI, install XenAPI.
        pip_install_gr xenapi
    fi

    # Get the path that os-xenapi is installed or the path that nova source code resides
    os_xenapi_dir=$(sudo -H pip show os-xenapi |grep "Location:"|cut -d " " -f 2-)
    if [ -n "$os_xenapi_dir" ]; then
        plugin_dir=$os_xenapi_dir/os_xenapi/dom0/etc/xapi.d/plugins/
        if [ -d $plugin_dir ]; then
            tar -czf - -C $plugin_dir ./ | $ssh_dom0 "tar -xzf - -C $dom0_plugin_dir"
        fi
    fi
    # change plugins to be executable
    $ssh_dom0 "chmod a+x $dom0_plugin_dir/*"
}

# Config iptables in Dom0
function config_dom0_iptables {
    local ssh_dom0=$(get_dom0_ssh)

    # Remove restriction on linux bridge in Dom0 so security groups
    # can be applied to the interim bridge-based network.
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
    $ssh_dom0 "iptables -t filter -C $XS_DOM0_IPTABLES_CHAIN -p tcp -m tcp --dport $DOM0_OVSDB_PORT -j ACCEPT"
    local remote_conn_result=$?
    if [ "$remote_conn_result" != "0" ]; then
        $ssh_dom0 "iptables -t filter -I $XS_DOM0_IPTABLES_CHAIN -p tcp --dport $DOM0_OVSDB_PORT -j ACCEPT"
    fi

    # Check iptables for VxLAN, add if not exist
    $ssh_dom0 "iptables -t filter -C $XS_DOM0_IPTABLES_CHAIN -p udp -m multiport --dports $DOM0_VXLAN_PORT -j ACCEPT"
    local vxlan_result=$?
    if [ "$vxlan_result" != "0" ]; then
        $ssh_dom0 "iptables -t filter -I $XS_DOM0_IPTABLES_CHAIN -p udp -m multiport --dport $DOM0_VXLAN_PORT -j ACCEPT"
    fi

    # Restore errexit setting
    $_ERREXIT_XENSERVER
}

# Configure ovs agent for compute node, i.e. q-domua
function config_ovs_agent {
    # TODO(huan): remove below line when https://review.openstack.org/#/c/435224/ merged
    sudo rm -f $NEUTRON_CORE_PLUGIN_CONF.domU

    # Make a copy of our config for domU
    sudo cp $NEUTRON_CORE_PLUGIN_CONF $NEUTRON_CORE_PLUGIN_CONF.domU

    # Change domU's config file to STACK_USER
    sudo chown $STACK_USER:$STACK_USER $NEUTRON_CORE_PLUGIN_CONF.domU

    # Configure xen configuration for neutron rootwrap.conf
    iniset $NEUTRON_ROOTWRAP_CONF_FILE xenapi xenapi_connection_url "$XENAPI_CONNECTION_URL"
    iniset $NEUTRON_ROOTWRAP_CONF_FILE xenapi xenapi_connection_username "$XENAPI_USER"
    iniset $NEUTRON_ROOTWRAP_CONF_FILE xenapi xenapi_connection_password "$XENAPI_PASSWORD"

    # Configure q-domua, use Dom0's hostname and concat suffix
    local ssh_dom0=$(get_dom0_ssh)
    local dom0_hostname=`$ssh_dom0 "hostname"`
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU DEFAULT host "${dom0_hostname}"

    # Configure xenapi for q-domua to use its xenserver rootwrap daemon
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU xenapi connection_url "$XENAPI_CONNECTION_URL"
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU xenapi connection_username "$XENAPI_USER"
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU xenapi connection_password "$XENAPI_PASSWORD"
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU agent root_helper ""
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU agent root_helper_daemon "xenapi_root_helper"

    # TODO(huanxie): Enable minimized polling now bug 1495423 is fixed
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU agent minimize_polling False

    # Set integration bridge for ovs-agent in compute node (q-domua)
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs integration_bridge $OVS_BRIDGE

    # Set OVS native interface for ovs-agent in compute node (q-domua)
    local dom0_ip=$(echo "$XENAPI_CONNECTION_URL" | cut -d "/" -f 3)
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs ovsdb_connection tcp:$dom0_ip:$DOM0_OVSDB_PORT
    iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs of_listen_address $HOST_IP

    if [[ "$ENABLE_TENANT_VLANS" == "True" ]]; then
        # Create a bridge "br-$VLAN_INTERFACE" and add port
        _neutron_ovs_base_add_bridge "br-$VLAN_INTERFACE"
        sudo ovs-vsctl -- --may-exist add-port "br-$VLAN_INTERFACE" $VLAN_INTERFACE

        # Set bridge mapping for q-domua which is for compute node
        iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs bridge_mappings "physnet1:$FLAT_NETWORK_BRIDGE"

        # Set bridge mappings for q-agt as we have an extra bridge mapping physnet1 for domU and dom0
        iniset $NEUTRON_CORE_PLUGIN_CONF ovs bridge_mappings "physnet1:br-$VLAN_INTERFACE,$PHYSICAL_NETWORK:$OVS_PHYSICAL_BRIDGE"

    elif [[ "$OVS_ENABLE_TUNNELING" == "True" ]]; then
        # Set tunnel ip for openvswitch agent in compute node (q-domua).
        # All q-domua's OVS commands are executed in Dom0, so the tunnel
        # is established between Dom0 and DomU(where DevStack runs), and
        # we need to set local_ip in q-domua that is used for Dom0
        iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs bridge_mappings ""
        iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs local_ip $dom0_ip
        iniset $NEUTRON_CORE_PLUGIN_CONF.domU ovs tunnel_bridge $OVS_TUNNEL_BRIDGE
    fi
}

function config_nova_compute {
    iniset $NOVA_CONF xenserver vif_driver nova.virt.xenapi.vif.XenAPIOpenVswitchDriver
    iniset $NOVA_CONF xenserver ovs_integration_bridge $OVS_BRIDGE
    iniset $NOVA_CONF DEFAULT firewall_driver nova.virt.firewall.NoopFirewallDriver
    # Configure nova-compute, use Dom0's hostname and concat suffix
    local ssh_dom0=$(get_dom0_ssh)
    local dom0_hostname=`$ssh_dom0 "hostname"`
    iniset $NOVA_CONF DEFAULT host "${dom0_hostname}"
}

function config_ceilometer {
    if is_service_enabled ceilometer-acompute; then
        local ssh_dom0=$(get_dom0_ssh)
        local dom0_hostname=`$ssh_dom0 "hostname"`
        iniset $CEILOMETER_CONF DEFAULT host "${dom0_hostname}"
        iniset $CEILOMETER_CONF DEFAULT hypervisor_inspector xenapi

        iniset $CEILOMETER_CONF xenapi connection_url "$XENAPI_CONNECTION_URL"
        iniset $CEILOMETER_CONF xenapi connection_username "$XENAPI_USER"
        iniset $CEILOMETER_CONF xenapi connection_password "$XENAPI_PASSWORD"

        # For XenAPI driver, we cannot use default value "libvirt_metadata"
        # https://github.com/openstack/ceilometer/blob/master/ceilometer/compute/discovery.py#L125
        iniset $CEILOMETER_CONF compute instance_discovery_method naive
    fi
}

# Start neutron-openvswitch-agent for Dom0 (q-domua)
function start_ovs_agent {
    local config_file="--config-file $NEUTRON_CONF --config-file $NEUTRON_CORE_PLUGIN_CONF.domU"

    # TODO(huanxie): neutron-legacy is deprecated, checking is_neutron_legacy_enabled
    # can make our code more compatible with devstack future changes, see link
    # https://github.com/openstack-dev/devstack/blob/master/lib/neutron-legacy#L62
    if is_neutron_legacy_enabled; then
        # TODO(huanxie): delete below when https://review.openstack.org/#/c/435224/ merged
        stop_process q-domua

        run_process q-domua "$AGENT_BINARY $config_file"
    else
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

function start_ceilometer_acompute {
    if is_service_enabled ceilometer-acompute; then
        run_process ceilometer-acompute "$CEILOMETER_BIN_DIR/ceilometer-polling --polling-namespaces compute --config-file $CEILOMETER_CONF"
    fi
}

# Remove Dom0 firewall rules created by this plugin
function cleanup_dom0_iptables {
    local ssh_dom0=$(get_dom0_ssh)

    # Save errexit setting
    _ERREXIT_XENSERVER=$(set +o | grep errexit)
    set +o errexit

    $ssh_dom0 "iptables -t filter -L $XS_DOM0_IPTABLES_CHAIN"
    local chain_result=$?
    if [ "$chain_result" == "0" ]; then
        $ssh_dom0 "iptables -t filter -F $XS_DOM0_IPTABLES_CHAIN"
        $ssh_dom0 "iptables -t filter -D INPUT -j $XS_DOM0_IPTABLES_CHAIN"
        $ssh_dom0 "iptables -t filter -X $XS_DOM0_IPTABLES_CHAIN"
    fi

    # Restore errexit setting
    $_ERREXIT_XENSERVER
}

# Prepare directories for kernels and images in Dom0
function create_dom0_kernel_and_image_dir {
    local ssh_dom0=$(get_dom0_ssh)

    {
        echo "set -eux"
        cat $OS_XENAPI_DIR/devstack/dom0_functions
        echo "create_directory_for_images"
        echo "create_directory_for_kernels"
    } | $ssh_dom0
}

# Install conntrack-tools in Dom0
function install_dom0_conntrack {
    local ssh_dom0=$(get_dom0_ssh)

    {
        echo "set -eux"
        cat $OS_XENAPI_DIR/devstack/dom0_functions
        echo "install_conntrack_tools"
    } | $ssh_dom0
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
            install_dom0_conntrack
            create_dom0_kernel_and_image_dir
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
            config_ceilometer
            ;;
        extra)
            # Called near the end after layer 1 and 2 services have been started
            start_ovs_agent
            start_ceilometer_acompute
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
    cleanup_dom0_iptables
elif [[ "$MODE" == "clean" ]]; then
    # Called by clean.sh before other services are cleaned, but after unstack.sh has been called
    cleanup_dom0_iptables
    # TODO(huanxie)
    # clean the OVS bridge created in Dom0?
fi
