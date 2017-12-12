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

"""Command get facts about XenAPI.

This command will return the facts about XenAPI in a json formatted dict.
e.g. 
'{"DOM0_HOST_NAME": "traya", "HIMN_LOCAL_IP": "169.254.0.2"}'
"""

import getopt
import os
import sys

import os_xenapi.utils.get_xenapi_facts as get_xenapi_facts


USAGE_MSG = "Run the following command to bootstrap the XenAPI environment:\n"
USAGE_MSG += sys.argv[0]
USAGE_MSG += " [-i|--himn-ip=] <XenServer's HIMN IP>"
USAGE_MSG += " [-u|--user-name=] <user-name>"
USAGE_MSG += " [-p|--passwd=] <passwd>\n\n"

VALID_OPS_SHORT_STR = "i:p:u:"
VALID_OPS_LONG_LST = ["himn-ip=","passwd=", "user-name="]


def exit_with_usage():
    sys.stderr.write(USAGE_MSG)
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        exit_with_usage()

    try:
        opts, args = getopt.getopt(sys.argv[1:],"i:p:u:",
                                   ["himn-ip=","passwd=", "user-name="])
    except getopt.GetoptError:
        exit_with_usage()

    if len(opts) != len(VALID_OPS_LONG_LST):
        exit_with_usage()

    # Get the values from input arguments and set in environ variables
    # so that they can be shared by all modules.
    for opt, arg in opts:
        if opt in ("-i", "--himn-ip"):
            os.environ["DOM0-HIMN-IP"] = arg
        elif opt in ("-p", "--passwd"):
            os.environ["DOM0-PASSWD"] = arg
        elif opt in ("-u", "--user-name"):
            os.environ["DOM0-USER-NAME"] = arg

    return get_xenapi_facts.main()

if __name__ == "__main__":
    sys.exit(main())
