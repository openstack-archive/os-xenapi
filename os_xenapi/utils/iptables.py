#!/usr/bin/env python
import logging
from os_xenapi.client import exception
from os_xenapi.utils import common_function
from os_xenapi.utils import himn

LOG = logging.getLogger('XenAPI_utils')

# For debug
# os.environ["DOM0-HIMN-IP"] = "169.254.0.1"
# os.environ["DOM0-USER-NAME"] = "root"
# os.environ["DOM0-PASSWD"] = "xenroot"

def configure_dom0_iptables(client):
    if not client:
        raise exception.IptableClientInvalid()
    xs_chain = 'XenServer-Neutron-INPUT'

    # Check XenServer specific chain, create if not exist
    commands = 'iptables -t filter -L %s;' % xs_chain + \
               'iptables -t filter --new %s;' % xs_chain + \
               'iptables -t filter -I INPUT -j %s' % xs_chain
    client.ssh(commands)

    # Check XenServer rule for ovs native mode, create if not exist
    commands = 'iptables -t filter -C %s -p tcp -m tcp --dport 6640 -j ' \
               'ACCEPT;' % xs_chain + \
               'iptables -t filter -I %s -p tcp --dport 6640 -j ACCEPT' \
               % xs_chain
    client.ssh(commands)

    # Check XenServer rule for vxlan, create if not exist
    commands = 'iptables -t filter -C %s -p udp -m multiport --dports 4789 ' \
               '-j ACCEPT;' % xs_chain + \
               'iptables -t filter -I %s -p udp -m multiport --dport 4789 -j '\
               'ACCEPT' % xs_chain
    client.ssh(commands)

    # Persist iptables rules
    client.ssh('service iptables save')

def configure_himn_forwards(end_point_eths, himn_dom0_ip):
    eth = himn.get_local_himn_eth(himn_dom0_ip)
    if not eth:
        raise exception.IptableNoNetworkInterface(himn_dom0_ip)
    for end_point in end_point_eths:
        # allow traffic from HIMN and forward traffic
        common_function.execute('/usr/bin/touch', '/tmp/test_by_himn')
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
