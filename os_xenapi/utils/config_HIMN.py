#!/usr/bin/env python
import logging
from os_xenapi.utils import common_utils
from os_xenapi.client import exception
import sys

LOG = logging.getLogger('HIMN')

def assert_not_none(tip, input):
    if not input:
        exc_log = "Error, " + tip + " is None"
        raise exception(exc_log)

def main(argv):
    if len(argv) != 3:
        raise exception("Missing arguments")
    dom0_himn_ip = argv[0]
    dom0_user_name = argv[1]
    dom0_password = argv[2]
    assert("dom0_himn_ip", dom0_himn_ip)
    assert("dom0_user_name", dom0_user_name)
    assert("dom0_password", dom0_password)

    eth, ip = common_utils.detect_himn()
    if not ip:
        LOG.warn("Can not get himn eth from eth list, access xenstore...")
        eth = common_utils.find_eth_xenstore()
    # populate the ifcfg file for HIMN interface, so that it will always get ip
    # in the future.
    ifcfg_file = '/etc/sysconfig/network-scripts/ifcfg-%s' % eth
    s = ('DEVICE="{eth}"\n'
         'IPV6INIT="no"\n'
         'BOOTPROTO="dhcp"\n'
         'DEFROUTE=no\n'
         'ONBOOT="yes"\n'.format(eth=eth))
    with open(ifcfg_file, 'w') as f:
        f.write(s)
        common_utils.execute('ifdown', eth)
        common_utils.execute('ifup', eth)

if __name__ == '__main__':
    main(sys.argv[1:])
