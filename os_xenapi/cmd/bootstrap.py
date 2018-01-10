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
import logging
import sys

from os_xenapi.utils.common_conf import enable_linux_bridge
from os_xenapi.utils.common_function import setup_logging
from os_xenapi.utils.himn import config_himn
from os_xenapi.utils.iptables import config_iptables
from os_xenapi.utils.sshclient import SSHClient
from os_xenapi.utils.xapi_plugin import install_plugins_to_dom0
from os_xenapi.utils.xenapi_facts import get_xenapi_facts

USAGE_MSG = "Run the following command to bootstrap the XenAPI compute node:\n"
USAGE_MSG += sys.argv[0]
USAGE_MSG += " [-i|--himn-ip] <XenServer's HIMN IP>"
USAGE_MSG += " [-f|--xenapi-facts-file] <file path to save xenapi facts in>"
USAGE_MSG += " [-u|--user-name] <user-name>"
USAGE_MSG += " [-p|--passwd] <passwd>\n\n"

DEF_XENAPI_FACTS_FILE = '/etc/xenapi_facts.json'

LOG = logging.getLogger(__name__)


def exit_with_usage():
    sys.stderr.write(USAGE_MSG)
    sys.exit(1)


def get_and_store_facts(dom0_client, file_path):
    facts = get_xenapi_facts(dom0_client)
    with open(file_path, 'w') as f:
        f.write(json.dumps(facts, indent=4, sort_keys=True))


def _parse_args(argv):
    VALID_OPS_SHORT_STR = "i:f:p:u:"
    VALID_OPS_LONG_LST = ["himn-ip", "xenapi-facts-file",
                          "passwd", "user-name"]
    MANDATORY_OPT_LST = ["himn-ip", "passwd", "user-name"]
    opt_values = {}

    if len(argv) < 2:
        return exit_with_usage()
    argv = argv[1:]

    try:
        opts, args = getopt.getopt(argv, VALID_OPS_SHORT_STR,
                                   VALID_OPS_LONG_LST)
    except getopt.GetoptError:
        return exit_with_usage()

    # Get the values from input parameters.
    for opt, arg in opts:
        if opt in ("-i", "--himn-ip"):
            opt_values['himn-ip'] = arg
        elif opt in ("-f", "--xenapi-facts-file"):
            opt_values['xenapi-facts-file'] = arg
        elif opt in ("-p", "--passwd"):
            opt_values['passwd'] = arg
        elif opt in ("-u", "--user-name"):
            opt_values['user-name'] = arg

    # Ensure mandatory opts are all provided.
    for opt in MANDATORY_OPT_LST:
        if opt not in opt_values:
            return exit_with_usage()

    return opt_values


def main():
    setup_logging(log_level=logging.DEBUG)

    opt_values = _parse_args(sys.argv)

    himn_ip = opt_values['himn-ip']
    user_name = opt_values['user-name']
    passwd = opt_values['passwd']
    # Use DEF_XENAPI_FACTS_FILE if none provided via commandline.
    facts_file = opt_values.get('xenapi-facts-file', DEF_XENAPI_FACTS_FILE)
    dom0_client = SSHClient(himn_ip, user_name, passwd)

    # Invoke functions to do needed boostrap tasks.
    LOG.info("Launch bootstrap task")
    config_himn(himn_ip)
    config_iptables(dom0_client)
    install_plugins_to_dom0(dom0_client)
    enable_linux_bridge(dom0_client)

    # Gather XenAPI relative facts and save them into file.
    get_and_store_facts(dom0_client, facts_file)

if __name__ == "__main__":
    sys.exit(main())
