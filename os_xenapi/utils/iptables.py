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

It contains the utiles relative to iptable settings."""
from os_xenapi.client import exception
from os_xenapi.utils import common_function
from os_xenapi.utils import himn
from os_xenapi.utils import sshclient
import sys

end_point_list = ['br-storage', 'br-mgmt']


def execute_dom0_iptables_commands(client, command_list):
    # Execute first command and continue based on first command result
    try:
        client.ssh(command_list[0], True, True)
    except sshclient.SshExecCmdFailure:
        if len(command_list) > 1:
            for command in command_list[1:]:
                client.ssh(command)


def configure_dom0_iptables(dom0_himn_ip, user_name, password):
    client = sshclient.SSHClient(dom0_himn_ip, user_name, password)
    if not client:
        raise exception.SSHClientInvalid()

    xs_chain = 'XenServer-Neutron-INPUT'

    # create XenServer specific chain
    commands = ('iptables -t filter -L %s;' % xs_chain,
                'iptables -t filter --new %s;' % xs_chain,
                'iptables -t filter -I INPUT -j %s' % xs_chain)
    execute_dom0_iptables_commands(client, commands)

    # create XenServer rule for ovs native mode
    commands = ('iptables -t filter -C %s -p tcp -m tcp --dport 6640 -j '
                'ACCEPT;' % xs_chain,
                'iptables -t filter -I %s -p tcp --dport 6640 -j ACCEPT'
                % xs_chain)
    execute_dom0_iptables_commands(client, commands)

    # create XenServer rule for vxlan
    commands = ('iptables -t filter -C %s -p udp -m multiport --dports 4789 '
                '-j ACCEPT;' % xs_chain,
                'iptables -t filter -I %s -p udp -m multiport --dport 4789 -j '
                'ACCEPT' % xs_chain)
    execute_dom0_iptables_commands(client, commands)

    # Persist iptables rules
    client.ssh('service iptables save')


def configure_himn_forwards(end_point_eths, dom0_himn_ip):
    eth = himn.get_local_himn_eth(dom0_himn_ip)
    if not eth:
        raise exception.NoNetworkInterfaceWithIp(dom0_himn_ip)
    for end_point in end_point_eths:
        # allow traffic from HIMN and forward traffic
        common_function.execute('iptables', '-t', 'nat', '-A', 'POSTROUTING',
                                '-o', end_point, '-j', 'MASQUERADE')
        common_function.execute('iptables', '-A', 'FORWARD',
                                '-i', end_point, '-o', eth,
                                '-m', 'state', '--state',
                                'RELATED,ESTABLISHED', '-j', 'ACCEPT')
        common_function.execute('iptables', '-A', 'FORWARD',
                                '-i', eth, '-o', end_point,
                                '-j', 'ACCEPT')
        common_function.execute('iptables', '-A', 'INPUT', '-i', eth, '-j',
                                'ACCEPT')
        common_function.execute('iptables', '-t', 'filter', '-S', 'FORWARD')
        common_function.execute('iptables', '-t', 'nat', '-S', 'POSTROUTING')


def config_iptables(dom0_himn_ip, user_name, password):
    configure_himn_forwards(end_point_list, dom0_himn_ip)
    configure_dom0_iptables(dom0_himn_ip, user_name, password)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise exception.MissingRequiredArguments()
    dom0_himn_ip, user_name, password = sys.argv[1:]
    config_iptables(dom0_himn_ip, user_name, password)
