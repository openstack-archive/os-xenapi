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


def get_hostname(host_client):
    out, _ = host_client.ssh('hostname')
    hostname = out.strip()
    return hostname


def get_facts(dom0_himn_ip, user_name, passwd):
    facts = {}

    dom0_client = sshclient.SSHClient(dom0_himn_ip, user_name, passwd)

    facts['hostname'] = get_hostname(dom0_client)

    # get local HIMN info
    eth = himn.get_local_himn_eth(dom0_himn_ip)
    ip_addr = common_function.get_eth_ipaddr(eth)
    facts['local_himn_eth'] = eth
    facts['local_himn_ip'] = ip_addr

    return json.dumps(facts)

if __name__ == '__main__':
    dom0_himn_ip, user_name, passwd = sys.argv[1:]
    facts_json = get_facts(dom0_himn_ip, user_name, passwd)
    print('get_facts returns:\n %s' % facts_json)
