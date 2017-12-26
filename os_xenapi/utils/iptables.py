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
    rule_spec = ('-L %s' % xs_chain)
    if not execute_iptables_cmd('filter', rule_spec, client, True):
        rule_spec = ('--new %s' % xs_chain)
        execute_iptables_cmd('filter', rule_spec, client)
        rule_spec = ('-I INPUT -j %s' % xs_chain)
        execute_iptables_cmd('filter', rule_spec, client)

    # Check XenServer rule for ovs native mode, create if not exist
    rule = ('-p tcp -m tcp --dport %s -j ACCEPT'
            % OVS_NATIVE_TCP_PORT)
    ensure_iptables(client, rule)

    # Check XenServer rule for vxlan, create if not exist
    rule = ('-p udp -m multiport --dport %s -j ACCEPT'
            % VXLAN_UDP_PORT)
    ensure_iptables(client, rule)

    # Persist iptables rules
    client.ssh('service iptables save', )


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
    for interface in forwarding_interfaces:
        # allow traffic from HIMN and forward traffic
        rule_spec = ['POSTROUTING', '-o', interface, '-j', 'MASQUERADE']
        ensure_iptables('nat', rule_spec)

        rule_spec = ['FORWARD', '-i', interface, '-o', eth, '-m', 'state',
                     '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT']
        ensure_iptables('filter', rule_spec)

        rule_spec = ['FORWARD', '-i', eth, '-o', interface, '-j', 'ACCEPT']
        ensure_iptables('filter', rule_spec)

        rule_spec = ['INPUT', '-i', eth, '-j', 'ACCEPT']
        ensure_iptables('filter', rule_spec)

    execute_iptables_cmd('filter', '-S FORWARD')
    execute_iptables_cmd('nat', '-S POSTROUTING')


def ensure_iptables(table, rule_spec, client=None):
    xs_chain = 'XenServer-Neutron-INPUT'
    rule_spec = ('-C %(xs_chain)s %(rule_spec)s'
                 % {'xs_chain': xs_chain, 'rule_spec': rule_spec})
    if execute_iptables_cmd(table, rule_spec, client, True):
        action = '-A'
        if client:
            action = '-I'
        rule_spec = ('%(action)s %(xs_chain)s %(rule_spec)s'
                     % {'action': action, 'xs_chain': xs_chain,
                        'rule_spec': rule_spec})
        execute_iptables_cmd(table, rule_spec, client)


def execute_iptables_cmd(table, rule_spec, client=None,
                         expect_exception=False):
    """This function is used to run iptables command.

    Users could run command to configure iptables for remote and local hosts.
    If the user want to configure remote host, the session client is needed, or
    the command would be run on local host.

    :param table: table you want you configure
    :param rule_spec: rule spec you want to apply
    :param client: session client with Dom0
    :param expect_exception: When you just want to do a rule check, set this
    flag to 'True'. Then the reture value would be 'Ture' or 'False'.
    :param forwarding_interfaces: network interface list which user want to
    forward HIMN packages.
    """
    if client:
        command = ('iptables -t %(table)s %(rule_spec)s'
                   % {'table': table, 'rule_spec': rule_spec})
        try:
            client.ssh(command)
        except client.SshExecCmdFailure:
            if expect_exception:
                return False
            else:
                raise
    else:
        spec_list = rule_spec.split()
        command = ['iptables', '-t', table] + spec_list
        try:
            common_function.execute(command)
        except exception.ExecuteCommandFailed:
            if expect_exception:
                return False
            else:
                raise
    return True


def config_iptables(client, forwarding_interfaces=None):
    """This function is used to configure iptables on a XenServer compute node.

    :param client: session client with Dom0
    :param forwarding_interfaces: network interface list which user want to
    forward HIMN packages.
    """
    if forwarding_interfaces:
        configure_himn_forwards(forwarding_interfaces, client.ip)
    configure_dom0_iptables(client)


if __name__ == '__main__':
    if len(sys.argv) != 5:
        exit_with_error("Wrong parameters input.")
    dom0_himn_ip, user_name, password, forwarding_interfaces = sys.argv[1:]
    try:
        client = sshclient.SSHClient(dom0_himn_ip, user_name, password)
    except Exception:
        exit_with_error("Create connection failed, ip: %(dom0_himn_ip)s,"
                        " user_name: %(user_name)s" %
                        {'dom0_himn_ip': dom0_himn_ip, 'user_name': user_name})
    config_iptables(client, forwarding_interfaces)
