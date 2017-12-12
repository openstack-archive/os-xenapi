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

"""Command for XenAPI bootstrap.

It contains any needed work to bootstrap a XenServer node, so that it's in
a good state to proceed for further OpenStack deployment."""

import getopt
import json
import sys

from os_xenapi.utils.himn import config_himn
from os_xenapi.utils.iptables import config_iptables
from os_xenapi.utils.sshclient import SSHClient
from os_xenapi.utils.xapi_plugin import install_plugins_to_dom0
from os_xenapi.utils.xenapi_facts import get_xenapi_facts

USAGE_MSG = "Run the following command to bootstrap the XenAPI compute node:\n"
USAGE_MSG += sys.argv[0]
USAGE_MSG += " [-i|--himn-ip] <XenServer's HIMN IP>"
USAGE_MSG += " [-u|--user-name] <user-name>"
USAGE_MSG += " [-p|--passwd] <passwd>\n\n"

XENAPI_FACTS_FILE = '/etc/xenapi_facts.json'

VALID_OPS_SHORT_STR = "i:p:u:"
VALID_OPS_LONG_LST = ["himn-ip", "passwd", "user-name"]


def exit_with_usage():
    sys.stderr.write(USAGE_MSG)
    sys.exit(1)


def get_and_store_facts(dom0_client, XENAPI_FACTS_FILE):
    facts = get_xenapi_facts(dom0_client)
    with open(XENAPI_FACTS_FILE, 'w') as f:
        f.write(json.dumps(facts, indent=4, sort_keys=True))


def _parse_args(argv):
    opt_values = {}

    if len(argv) < 2:
        return exit_with_usage()
    argv = argv[1:]

    try:
        opts, args = getopt.getopt(argv, VALID_OPS_SHORT_STR,
                                   VALID_OPS_LONG_LST)
    except getopt.GetoptError:
        return exit_with_usage()

    if len(opts) != len(VALID_OPS_LONG_LST):
        return exit_with_usage()

    # Get the values from input parameters.
    for opt, arg in opts:
        if opt in ("-i", "--himn-ip"):
            opt_values['himn_ip'] = arg
        elif opt in ("-p", "--passwd"):
            opt_values['passwd'] = arg
        elif opt in ("-u", "--user-name"):
            opt_values['user_name'] = arg

    return opt_values


def main():
    opt_values = _parse_args(sys.argv)

    himn_ip = opt_values['himn_ip']
    user_name = opt_values['user_name']
    passwd = opt_values['passwd']
    dom0_client = SSHClient(himn_ip, user_name, passwd)

    # Invoke functions to do needed boostrap tasks.
    config_himn(himn_ip)
    config_iptables(dom0_client)
    install_plugins_to_dom0(dom0_client)

    # Gather XenAPI relative facts and save them into file.
    get_and_store_facts(dom0_client, XENAPI_FACTS_FILE)

if __name__ == "__main__":
    sys.exit(main())
