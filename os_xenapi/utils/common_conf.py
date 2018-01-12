# Copyright 2018 Citrix Systems
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

"""The configure utils

It contains the configure operations."""
import sys

from os_xenapi.utils import common_function
from os_xenapi.utils import sshclient


def enable_linux_bridge(dom0_client):
    # disable to bridge blacklist to allow linux bridge create on Dom0

    dom0_client.ssh("if [ -f /etc/modprobe.d/blacklist-bridge.conf ]; then\n"
                    "    mv -f /etc/modprobe.d/blacklist-bridge.conf"
                    "        /etc/modprobe.d/blacklist-bridge.conf_bak\n"
                    "fi")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        common_function.exit_with_error("Wrong parameters input.")
    dom0_himn_ip, user_name, password = sys.argv[1:]
    dom0_client = sshclient.SSHClient(dom0_himn_ip, user_name, password)
    enable_linux_bridge(dom0_client)
