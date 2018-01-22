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
    ret, out, err = execute_iptables_cmd('filter', '-L', xs_chain,
                                         client=client,
                                         allowed_return_codes=[0, 1])
    if ret == 1:
        execute_iptables_cmd('filter', '--new', xs_chain, client=client)
        rule_spec = ('-j %s' % xs_chain)
        execute_iptables_cmd('filter', '-I', 'INPUT', rule_spec=rule_spec,
                             client=client)

    # Check XenServer rule for ovs native mode, create if not exist
    rule_spec = ('-p tcp -m tcp --dport %s -j ACCEPT'
                 % OVS_NATIVE_TCP_PORT)
    ensure_iptables('filter', xs_chain, rule_spec, client=client)

    # Check XenServer rule for vxlan, create if not exist
    rule_spec = ('-p udp -m multiport --dport %s -j ACCEPT'
                 % VXLAN_UDP_PORT)
    ensure_iptables('filter', xs_chain, rule_spec, client=client)

    # Persist iptables rules
    client.ssh('service iptables save')


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
        rule_spec = '-o ' + interface + ' -j MASQUERADE'
        ensure_iptables('nat', 'POSTROUTING', rule_spec)

        rule_spec = '-i ' + interface + ' -o ' + eth + ' -m state ' + \
                    '--state RELATED,ESTABLISHED -j ACCEPT'
        ensure_iptables('filter', 'FORWARD', rule_spec)

        rule_spec = '-i ' + eth + ' -o ' + interface + ' -j ACCEPT'
        ensure_iptables('filter', 'FORWARD', rule_spec)

    rule_spec = '-i ' + eth + ' -j ACCEPT'
    ensure_iptables('filter', 'INPUT', rule_spec)
    execute_iptables_cmd('filter', '-S', 'FORWARD')
    execute_iptables_cmd('nat', '-S', 'POSTROUTING')


def ensure_iptables(table, chain, rule_spec, client=None):
    ret, _, _ = execute_iptables_cmd(
        table, '-C', chain, rule_spec=rule_spec, client=client,
        allowed_return_codes=[0, 1])
    # if the return value is 1, the rule is not exists
    if ret == 1:
        execute_iptables_cmd(table, '-I', chain, rule_spec=rule_spec,
                             client=client)


def execute_iptables_cmd(table, action, chain, rule_spec=None, client=None,
                         allowed_return_codes=[0]):
    """This function is used to run iptables command.

    Users could run command to configure iptables for remote and local hosts.
    If the user want to configure remote host, the session client is needed, or
    the command would be run on local host.

    :param table: table you want you configure.
    :param rule_spec: rule spec you want to apply.
    :param client: session client to remote host you want to configure.
    :param expect_exception: When you just want to do a rule check, set this
    flag to 'True'. Then the reture value would be 'Ture' or 'False'.
    :param forwarding_interfaces: network interface list which user want to
    forward HIMN packages.
    """
    if client:
        if not rule_spec:
            rule_spec = ''
        command = ('iptables -t %(table)s %(action)s %(chain)s %(rule_spec)s'
                   % {'table': table, 'action': action,
                      'chain': chain, 'rule_spec': rule_spec})
        command = command.strip()
        return client.ssh(command, allowed_return_codes=allowed_return_codes)
    else:
        if rule_spec:
            rule_spec = rule_spec.split()
        else:
            rule_spec = []
        command = ['iptables', '-t', table, action, chain] + rule_spec
        return common_function.detailed_execute(
            *command, allowed_return_codes=allowed_return_codes)


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
    forwarding_interfaces = forwarding_interfaces.split()
    try:
        client = sshclient.SSHClient(dom0_himn_ip, user_name, password)
    except Exception:
        exit_with_error("Create connection failed, ip: %(dom0_himn_ip)s,"
                        " user_name: %(user_name)s" %
                        {'dom0_himn_ip': dom0_himn_ip, 'user_name': user_name})
    config_iptables(client, forwarding_interfaces)
