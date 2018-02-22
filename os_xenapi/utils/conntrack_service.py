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
"""conntrack service utils

It contains the utilities relative to conntrack service"""
import logging
import sys

from os_xenapi.utils import common_function
from os_xenapi.utils import sshclient

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def ensure_conntrack_packages(dom0_client):
    # Ensure the package be installed for conntrack service
    LOG.info("Ensure the package be installed for conntrack service")

    common_function.scp_and_execute(dom0_client, "install_conntrack.sh")


def enable_conntrack_service(dom0_client):
    # use conntrack statistic mode, so change conntrackd.conf
    LOG.info("enable conntrack service")
    ensure_conntrack_packages(dom0_client)

    common_function.scp_and_execute(dom0_client, "enable_conntrack.sh")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        common_function.exit_with_error("Wrong parameters input.")
    dom0_himn_ip, user_name, password = sys.argv[1:]
    dom0_client = sshclient.SSHClient(dom0_himn_ip, user_name, password)
    enable_conntrack_service(dom0_client)
