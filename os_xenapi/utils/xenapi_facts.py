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

"""Utilies for XenAPI facts gathering

It contains utilies to gather XenAPI relative facts."""

import json
import sys

from os_xenapi.utils import common_function
from os_xenapi.utils import himn
from os_xenapi.utils import sshclient


def get_xenapi_facts(dom0_client):
    """Get XenAPI facts

    This function will get XenAPI relative facts on the compute node:
    dom0_hostname: dom0's hostname.
    domu_himn_eth: domU's network interface which is connected to HIMN
    domu_himn_ip: domU's ip which belong to the subnt reserved for HIMN

    :param dom0_client: the remote access client connected to dom0
    :returns: a dict which contains all facts gathered.
    """

    facts = {}

    # get dom0's hostname
    facts['dom0_hostname'] = common_function.get_remote_hostname(dom0_client)
    # get dom0's IPs
    facts['dom0_ipv4s'] = common_function.get_host_ipv4s(dom0_client)

    # get domU's eth and ip which are connected to HIMN.
    eth = himn.get_local_himn_eth(dom0_client.ip)
    ip_addr = common_function.get_eth_ipaddr(eth)
    facts['domu_himn_eth'] = eth
    facts['domu_himn_ip'] = ip_addr

    # get domU eths' vif data
    facts['domu_vifs'] = common_function.get_domu_vifs_by_eth(dom0_client)

    return facts


if __name__ == '__main__':
    # Run in domU which has an interface connected to HIMN
    # argv[1]: dom0's IP address
    # argv[2]: user name
    # argv[3]: user passwd
    ssh_client = sshclient.SSHClient(sys.argv[1], sys.argv[2], sys.argv[3])
    print('Got XenAPI facts as:\n%s' % json.dumps(get_xenapi_facts(ssh_client),
                                                  indent=4, sort_keys=True))
