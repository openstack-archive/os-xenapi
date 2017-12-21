#!/usr/bin/env python
import netifaces
from os_xenapi.utils import common_function
from os_xenapi.client import exception
import sys

def find_himn_eth_xenstore():
    domid = common_function.execute('xenstore-read', 'domid')
    himn_mac = common_function.execute(
        'xenstore-read',
        '/local/domain/%s/vm-data/himn_mac' % domid)

    eths = [eth for eth in netifaces.interfaces()
            if common_function.eth_to_mac(eth) == himn_mac]
    if len(eths) != 1:
        raise exception('Cannot find eth matches himn_mac')

    return eths[0]

def detect_himn(dom0_himn_ip, eths=None):
    if eths is None:
        eths = netifaces.interfaces()
    for eth in eths:
        ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)
        if ip is None:
            continue
        himn_local = ip[0]['addr']
        himn_xs = '.'.join(himn_local.split('.')[:-1] + ['1'])
        if dom0_himn_ip == himn_xs:
            return eth, ip
    return None, None

def detect_dom0_himn_interface(client):
    out = None
    if client is not None:
        out = client.ssh("Get network interface of HIMN",
                         "xe network-list name-label='Host "
                         "internal management network'  | grep 'bridge' "
                         "| awk '{print $4}'",
                         output=True).strip("\n")
    return out

def config_himn(himn_dom0_ip):
    eth, ip = detect_himn(himn_dom0_ip)
    if not ip:
        eth = common_function.find_himn_eth_xenstore()
    # populate the ifcfg file for HIMN interface, so that it will always get ip
    # in the future.
    if not eth:
        raise exception("can't find eth on %s" % himn_dom0_ip)
    ifcfg_file = '/etc/sysconfig/network-scripts/ifcfg-%s' % eth
    s = ('DEVICE="{eth}"\n'
         'IPV6INIT="no"\n'
         'BOOTPROTO="dhcp"\n'
         'DEFROUTE=no\n'
         'ONBOOT="yes"\n'.format(eth=eth))
    with open(ifcfg_file, 'w') as f:
        f.write(s)
    common_function.execute('ifdown', eth)
    common_function.execute('ifup', eth)

if __name__ == '__main__':
    config_himn(sys.argv[1])
