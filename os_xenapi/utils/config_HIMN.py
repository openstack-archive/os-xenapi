#!/usr/bin/env python
import common_utils
import logging
import os
from sshclient import SSHClient
import sys

LOG = logging.getLogger('HIMN')

def main(argv):
    env_set = set(["DOM0-HIMN-IP", "DOM0-USER-NAME", "DOM0-PASSWD"])
    if not env_set <= set(os.environ.keys()):
        exc_log = "Environment variables missing: ip, user name, password"
        common_utils.reportError(exc_log)

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

    client = SSHClient(os.environ["DOM0-HIMN-IP"],
                       os.environ["DOM0-USER-NAME"],
                       os.environ["DOM0-PASSWD"])
    network_interface = common_utils.detect_interface(client)
    # allow traffic from HIMN and forward traffic
    common_utils.execute('/usr/bin/touch', '/tmp/test_by_himn')
    common_utils.execute('iptables', '-t', 'nat', '-A', 'POSTROUTING',
                         '-o', network_interface, '-j', 'MASQUERADE')
    common_utils.execute('iptables', '-A', 'FORWARD',
                         '-i', network_interface, '-o', eth,
                         '-m', 'state', '--state', 'RELATED,ESTABLISHED',
                         '-j', 'ACCEPT')
    common_utils.execute('iptables', '-A', 'FORWARD',
                         '-i', eth, '-o', network_interface,
                         '-j', 'ACCEPT')
    common_utils.execute('iptables', '-A', 'INPUT', '-i', eth, '-j', 'ACCEPT')
    common_utils.execute('iptables', '-t', 'filter', '-S', 'FORWARD')
    common_utils.execute('iptables', '-t', 'nat', '-S', 'POSTROUTING')


if __name__ == '__main__':
    main(sys.argv[1:])
