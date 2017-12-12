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

import json
import sys


def _get_dom0_hostname():
    # TODO(jianghuaw): get dom0's hostname
    HOSTNAME = "traya"
    return HOSTNAME


def _get_himn_local_ip():
    # TODO(jianghuaw): detect local HIMN interface and return the allocated
    # IP address.
    IP = '169.254.0.2'
    return IP


def main():
    facts = {}
    facts['DOM0_HOSTNAME'] = _get_dom0_hostname()
    facts['HIMN_LOCAL_IP'] = _get_himn_local_ip()
    print(json.dumps(facts))


if __name__ == "__main__":
    sys.exit(main())
