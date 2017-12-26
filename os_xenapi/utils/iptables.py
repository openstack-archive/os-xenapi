#!/usr/bin/env python
# Copyright 2017 Citrix Systems
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
"""iptable utils

It contains the utilities relative to iptable settings."""

import sys

from os_xenapi.client import exception
from os_xenapi.utils import common_function
from os_xenapi.utils import himn
from os_xenapi.utils import sshclient


OVS_NATIVE_TCP_PORT = '6640'
VXLAN_UDP_PORT = '4789'


def exit_with_error(err_msg):
    sys.stderr.write(err_msg)
    sys.exit(1)


def configure_dom0_iptables(client):
    xs_chain = 'XenServer-Neutron-INPUT'
    # Check XenServer specific chain, create if not exist
    commands = ('iptables -t filter -L %s' % xs_chain, )
    try:
        execute_dom0_iptables_commands(client, commands)
    except sshclient.SshExecCmdFailure:
        commands = ('iptables -t filter --new %s' % xs_chain,
                    'iptables -t filter -I INPUT -j %s' % xs_chain)
        execute_dom0_iptables_commands(client, commands)

    # Check XenServer rule for ovs native mode, create if not exist
    commands = ('iptables -t filter -C %(xs_chain)s -p tcp -m tcp --dport '
                '%(ovs_port)s -j ACCEPT'
                % {'xs_chain': xs_chain, 'ovs_port': OVS_NATIVE_TCP_PORT}, )
    try:
        execute_dom0_iptables_commands(client, commands)
    except sshclient.SshExecCmdFailure:
        commands = ('iptables -t filter -I %(xs_chain)s -p tcp --dport '
                    '%(ovs_port)s -j ACCEPT'
                    % {'xs_chain': xs_chain, 'ovs_port': OVS_NATIVE_TCP_PORT},
                    )
        execute_dom0_iptables_commands(client, commands)

    # Check XenServer rule for vxlan, create if not exist
    commands = ('iptables -t filter -C %(xs_chain)s -p udp -m multiport '
                '--dports %(vxlan_port)s -j ACCEPT'
                % {'xs_chain': xs_chain, 'vxlan_port': VXLAN_UDP_PORT}, )
    try:
        execute_dom0_iptables_commands(client, commands)
    except sshclient.SshExecCmdFailure:
        commands = ('iptables -t filter -I %(xs_chain)s -p udp -m multiport '
                    '--dport %(vxlan_port)s -j ACCEPT'
                    % {'xs_chain': xs_chain, 'vxlan_port': VXLAN_UDP_PORT}, )
        execute_dom0_iptables_commands(client, commands)

    # Persist iptables rules
    commands = ('service iptables save', )
    execute_dom0_iptables_commands(client, commands)


def execute_dom0_iptables_commands(client, command_list):
    # Execute first command and continue based on first command result
    if len(command_list) > 0:
        for command in command_list:
            client.ssh(command)


def configure_himn_forwards(forwarding_interfaces, dom0_himn_ip):
    # enable forward
    # make change to be persistent
    common_function.execute(
        'sed', '-i', 's/.*net\.ipv4\.ip_forward.*=.*/net.ipv4.ip_forward=1/g',
        '/etc/sysctl.conf')
    # make it to take effective now.
    common_function.execute('sysctl', 'net.ipv4.ip_forward=1')
    eth = himn.get_local_himn_eth(dom0_himn_ip)
    if not eth:
        raise exception.NoNetworkInterfaceInSameSegment(dom0_himn_ip)
    for end_point in forwarding_interfaces:
        # allow traffic from HIMN and forward traffic
        try:
            common_function.execute('iptables', '-t', 'nat', '-C',
                                    'POSTROUTING', '-o', end_point, '-j',
                                    'MASQUERADE')
        except exception.ExecuteCommandFailed:
            common_function.execute('iptables', '-t', 'nat', '-A',
                                    'POSTROUTING', '-o', end_point, '-j',
                                    'MASQUERADE')
        try:
            common_function.execute('iptables', '-C', 'FORWARD',
                                    '-i', end_point, '-o', eth,
                                    '-m', 'state', '--state',
                                    'RELATED,ESTABLISHED', '-j', 'ACCEPT')
        except exception.ExecuteCommandFailed:
            common_function.execute('iptables', '-A', 'FORWARD',
                                    '-i', end_point, '-o', eth,
                                    '-m', 'state', '--state',
                                    'RELATED,ESTABLISHED', '-j', 'ACCEPT')
        try:
            common_function.execute('iptables', '-C', 'FORWARD',
                                    '-i', eth, '-o', end_point,
                                    '-j', 'ACCEPT')
        except exception.ExecuteCommandFailed:
            common_function.execute('iptables', '-A', 'FORWARD',
                                    '-i', eth, '-o', end_point,
                                    '-j', 'ACCEPT')
        try:
            common_function.execute('iptables', '-C', 'INPUT', '-i', eth, '-j',
                                    'ACCEPT')
        except exception.ExecuteCommandFailed:
            common_function.execute('iptables', '-A', 'INPUT', '-i', eth, '-j',
                                    'ACCEPT')

    common_function.execute('iptables', '-t', 'filter', '-S', 'FORWARD')
    common_function.execute('iptables', '-t', 'nat', '-S', 'POSTROUTING')


def config_iptables(dom0_himn_ip, client, end_point_list):
    """This function is used to configure iptables on a XenServer compute node.

    :param client: session client with Dom0
    :param end_point_list: network interface list which user want to forward
    HIMN packages.
    """
    if end_point_list:
        configure_himn_forwards(end_point_list, dom0_himn_ip)
    configure_dom0_iptables(client)


if __name__ == '__main__':
    if len(sys.argv) != 5:
        exit_with_error("Wrong parameters input.")
    dom0_himn_ip, user_name, password, end_point_list = sys.argv[1:]
    try:
        client = sshclient.SSHClient(dom0_himn_ip, user_name, password)
    except Exception:
        exit_with_error("Create connection failed, ip: %(dom0_himn_ip)s,"
                        " user_name: %(user_name)s" %
                        {'dom0_himn_ip': dom0_himn_ip, 'user_name': user_name})
    config_iptables(dom0_himn_ip, client, end_point_list)
