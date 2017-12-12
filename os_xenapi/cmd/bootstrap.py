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
import sys

from os_xenapi.utils.himn import config_himn
from os_xenapi.utils.sshclient import SSHClient
from os_xenapi.utils.xapi_plugin import install_plugins_to_dom0

USAGE_MSG = "Run the following command to bootstrap the XenAPI compute node:\n"
USAGE_MSG += sys.argv[0]
USAGE_MSG += " [-i|--himn-ip] <XenServer's HIMN IP>"
USAGE_MSG += " [-u|--user-name] <user-name>"
USAGE_MSG += " [-p|--passwd] <passwd>\n\n"

VALID_OPS_SHORT_STR = "i:p:u:"
VALID_OPS_LONG_LST = ["himn-ip", "passwd", "user-name"]


def exit_with_usage():
    sys.stderr.write(USAGE_MSG)
    sys.exit(1)


def main(argv):
    try:
        opts, args = getopt.getopt(argv, VALID_OPS_SHORT_STR,
                                   VALID_OPS_LONG_LST)
    except getopt.GetoptError:
        exit_with_usage()

    if len(opts) != len(VALID_OPS_LONG_LST):
        exit_with_usage()

    # Get the values from input parameters.
    for opt, arg in opts:
        if opt in ("-i", "--himn-ip"):
            himn_ip = arg
        elif opt in ("-p", "--passwd"):
            passwd = arg
        elif opt in ("-u", "--user-name"):
            user_name = arg

    dom0_client = SSHClient(himn_ip, user_name, passwd)

    # Invoke modules' function to do needed boostrap operations.
    config_himn(himn_ip)
    install_plugins_to_dom0(dom0_client)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        exit_with_usage()

    sys.exit(main(sys.argv[1:]))
