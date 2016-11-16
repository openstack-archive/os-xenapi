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

# Save trace setting
_XTRACE_XENSERVER=$(set +o | grep xtrace)
set +o xtrace

MODE=$1
PHASE=$2

OS_XENAPI_DIR=$DEST/os-xenapi
DOM0_PLUGIN_DIR="/etc/xapi.d/plugins"

function get_dom0_ssh {
    local dom0_ip
    dom0_ip=$(echo "$XENAPI_CONNECTION_URL" | cut -d "/" -f 3)

    local ssh_dom0
    ssh_dom0="sudo -u $DOMZERO_USER ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$dom0_ip"
    echo $ssh_dom0
}

# TODO(huanxie) This is temporary as os-xenapi real content isn't on pypi
function install_domU_plugins {
    sudo -H pip install git+https://github.com/openstack/os-xenapi.git
}

function install_dom0_plugins {
    local ssh_dom0
    ssh_dom0=$(get_dom0_ssh)
    echo $ssh_dom0

    tar -czf - -C $OS_XENAPI_DIR/os_xenapi/dom0/etc/xapi.d/plugins/ ./ |
        $ssh_dom0 "tar -xzf - -C $DOM0_PLUGIN_DIR && chmod a+x $DOM0_PLUGIN_DIR/*"
}

if [[ "$MODE" == "stack" ]]; then
    case "$PHASE" in
        install)
            install_dom0_plugins

            # TODO(huanxie) Delete this when os-xenapi on pypi
            install_domU_plugins
            ;;
        post-config)
            # Called after the layer 1 and 2 services have been configured.
            # All configuration files for enabled services should exist at this point.
            # TODO(huanxie) when reverse q-agt/q-domua merged, q-domua is XS specific part
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

# Restore xtrace
$_XTRACE_XENSERVER
