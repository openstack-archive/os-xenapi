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
"""conntrack service utils

It contains the utiles relative to conntrack service"""

import sys

from os_xenapi.utils import sshclient


CONNTRACK_CONF_SAMPLE =\
    '/usr/share/doc/conntrack-tools-1.4.2/doc/stats/conntrackd.conf'


def exit_with_error(err_msg):
    sys.stderr.write(err_msg)
    sys.exit(1)


def enable_conntrack_service(dom0_himn_ip, user_name, password,
                             contrackd_conf_dir=CONNTRACK_CONF_SAMPLE):
    # use conntrack statistic mode, so change conntrackd.conf
    client = None
    try:
        client = sshclient.SSHClient(dom0_himn_ip, user_name, password)
    except Exception:
        exit_with_error("Create connection failed, ip: %(dom0_himn_ip)s,"
                        " user_name: %(user_name)s" %
                        {'dom0_himn_ip': dom0_himn_ip, 'user_name': user_name})
        return

    try:
        client.ssh('ls /etc/conntrackd/conntrackd.conf.back')
    except sshclient.SshExecCmdFailure:
        # Only make conntrackd.conf.back if it doesn't exist
        try:
            client.ssh('mv /etc/conntrackd/conntrackd.conf '
                       '/etc/conntrackd/conntrackd.conf.back')
        except sshclient.SshExecCmdFailure:
            pass

    client.ssh('cp ' + contrackd_conf_dir +
               ' /etc/conntrackd/conntrackd.conf')

    # Rotate log file for conntrack
    client.scp('/etc/logrotate.d/conntrackd', '/etc/logrotate.d/conntrackd')

    # Restart conntrackd service
    client.ssh('service conntrackd restart')


if __name__ == '__main__':
    if len(sys.argv) != 5:
        exit_with_error("Wrong parameters input.")
    dom0_himn_ip, user_name, password, contrackd_conf_dir = sys.argv[1:]
    enable_conntrack_service(dom0_himn_ip, user_name, password,
                             contrackd_conf_dir)
