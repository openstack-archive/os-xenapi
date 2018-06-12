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
"""console utils

It contains the utilities relative to guest VM console logs collecting."""
import os
import subprocess
import sys

from os_xenapi.utils import sshclient


def exit_with_error(err_msg):
    sys.stderr.write(err_msg)
    sys.exit(1)


def setup_guest_console_log(dom0_client):
    "Install console logrotate script"

    dom0_client.ssh('mkdir -p /var/log/xen/guest')
    dom0_client.ssh('mkdir -p /opt/xensource/bin')

    proc_show = subprocess.Popen("pip show os-xenapi".split(),
                                 stdin=subprocess.PIPE,  # nosec
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    proc_grep = subprocess.Popen("grep Location".split(),
                                 stdin=proc_show.stdout,  # nosec
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    proc_show.stdout.close()
    proc_awk = subprocess.Popen(["awk", "{print $2}"],
                                stdin=proc_grep.stdout,  # nosec
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    proc_grep.stdout.close()

    (out, err) = proc_awk.communicate()
    if out:
        # Truncate "\n" if it is the last char
        out = out.strip()
    elif err:
        return

    dom0_client.scp(
        out + "/rotate_xen_guest_logs.sh",
        os.path.join("/opt/xensource/bin/", 'rotate_xen_guest_logs.sh'))
    dom0_client.ssh('''crontab - << CRONTAB
* * * * * /opt/xensource/bin/rotate_xen_guest_logs.sh >/dev/null 2>&1
CRONTAB''')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        exit_with_error("Wrong parameters input.")
    dom0_himn_ip, user_name, password = sys.argv[1:]
    try:
        client = sshclient.SSHClient(dom0_himn_ip, user_name, password)
    except Exception:
        exit_with_error("Create connection failed, ip: %(dom0_himn_ip)s,"
                        " user_name: %(user_name)s" %
                        {'dom0_himn_ip': dom0_himn_ip, 'user_name': user_name})
    setup_guest_console_log(client)
