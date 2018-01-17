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
"""HIMN utils

It contains the utiles relative to HIMN(Host Internal Management Network."""

import ipaddress
import netifaces
import sys

from os_xenapi.client import exception
from os_xenapi.utils import common_function


def get_local_himn_eth_via_xenstore():
    # Find HIMN eth by querying xenstore.
    domid = common_function.execute('xenstore-read', 'domid')
    himn_mac = common_function.execute(
        'xenstore-read',
        '/local/domain/%s/vm-data/himn_mac' % domid)

    eths = [eth for eth in netifaces.interfaces()
            if common_function.get_eth_mac(eth) == himn_mac]
    if len(eths) != 1:
        raise exception.GetInterfaceOnHIMNMacError(himn_mac)

    return eths[0]


def get_local_himn_eth_via_ip(ip_in_himn, eths=None):
    # Get the local interface which is connected to HIMN by searching
    # an eth whose IP address is in the same network as `ip_in_himn`.
    # By default search all available interfaces. The parameter of
    # `eths` can be used to specify a list of interfaces, so that
    # it will only search interfaces belong to the list.
    if eths is None:
        eths = netifaces.interfaces()
    for eth in eths:
        ipv4s = netifaces.ifaddresses(eth).get(netifaces.AF_INET, [])
        for ipv4 in ipv4s:
            net_if = ipaddress.IPv4Interface(
                ipv4['addr'] + u'/' + ipv4['netmask'])
            if isinstance(ip_in_himn, bytes):
                ip_in_himn = ip_in_himn.decode('utf-8')
            hint_himn_ipaddr = ipaddress.ip_address(ip_in_himn)
            if hint_himn_ipaddr in net_if.network:
                # Got the interface which has an IP address belong to HIMN.
                return eth
    return None


def get_local_himn_eth(himn_dom0_ip):
    eth = get_local_himn_eth_via_ip(himn_dom0_ip)
    if eth:
        return eth
    # the local HIMN interfae has not got IP address: e.g. the interface
    # is not up or has not requested DHCP address; then try to get eth
    # via xenstore.
    return get_local_himn_eth_via_xenstore()


def persist_eth_cfg(eth, bootproto='dhcp', defroute='no', onboot='yes'):
    # Persist eth configure into ifcfg-eth file.
    ifcfg_file = '/etc/sysconfig/network-scripts/ifcfg-%s' % eth
    with open(ifcfg_file, 'w') as ifcfg:
        ifcfg.write('DEVICE="%s"\n' % eth)
        ifcfg.write('IPV6INIT="no"\n')
        ifcfg.write('BOOTPROTO="%s"\n' % bootproto)
        ifcfg.write('DEFROUTE="%s"\n' % defroute)
        ifcfg.write('ONBOOT="%s"\n' % onboot)


def config_himn(himn_dom0_ip):
    eth = get_local_himn_eth(himn_dom0_ip)
    # populate the ifcfg file for HIMN interface, so that it will always get ip
    # in the future.
    if not eth:
        raise exception.NoNetworkInterfaceInSameSegment(himn_dom0_ip)
    persist_eth_cfg(eth)
    # Force a restart on this interface by using the configure file.
    # It will ensure the interface up and refresh IP via DHCP.
    # NOTE(jianghuaw): use ifconfig to activate interface firstly.
    common_function.execute('ifconfig', eth, 'up')
    common_function.execute('ifdown', eth)
    common_function.execute('ifup', eth)


if __name__ == '__main__':
    config_himn(sys.argv[1])
