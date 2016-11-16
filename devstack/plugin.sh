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

# TODO(huaxie) will change this later
#OS_XENAPI_DIR=$DEST/os-xenapi
OS_XENAPI_DIR=/opt/stack/os-xenapi

function get_dom0_ssh {
    local dom0_ip
    dom0_ip=$(echo "$XENAPI_CONNECTION_URL" | cut -d "/" -f 3)

    local ssh_dom0
    ssh_dom0="sudo -u $DOMZERO_USER ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$dom0_ip"
    echo $ssh_dom0
    return 0
}

# Install
function install_plugins {
    local ssh_dom0
    ssh_dom0=$(get_dom0_ssh)

    local dom0_func
    dom0_func=`cat $OS_XENAPI_DIR/devstack/dom0_functions`
    local dom0_plugin_dir
    dom0_plugin_dir=`$ssh_dom0 "$dom0_func; set -eux; dom0_plugin_location"`

    # Get the path that os-xenapi is installed
    local plugin_dir
    plugin_dir=$(sudo -H pip show os-xenapi |grep "Location:"|cut -d " " -f 2-)
    tar -czf - -C $plugin_dir/os_xenapi/dom0/etc/xapi.d/plugins/ ./ |
        $ssh_dom0 "tar -xzf - -C $dom0_plugin_dir && chmod a+x $dom0_plugin_dir/*"
}

if [[ "$MODE" == "stack" ]]; then
    case "$PHASE" in
        install)
            install_plugins
            ;;
        post-config)
            # Called after the layer 1 and 2 services have been configured.
            # All configuration files for enabled services should exist at this point.
            # TODO(huanxie): when reverse q-agt/q-domua merged, q-domua is XS specific part
            # Configure XenServer neutron specific items for q-domua
            # ovs native mode
            # ovs VxLAN
            ;;
        extra)
            ;;
        test-config)
            # Called at the end of devstack used to configure tempest
            # or any other test environments
            # TODO(huanxie) Maybe we can set some conf here for CI?
            ;;
    esac
elif [[ "$MODE" == "clean" ]]; then
    # Called by clean.sh before other services are cleaned, but after unstack.sh has been called
    # TODO(huanxie)
    # Stop q-domua in the future?
    # clean the OVS bridge created in Dom0 and iptables rules?
    echo "mode is clean"
fi
