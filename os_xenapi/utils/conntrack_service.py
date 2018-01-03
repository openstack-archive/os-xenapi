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

import sys

from os_xenapi.utils import common_function
from os_xenapi.utils import sshclient


CONNTRACK_CONF_SAMPLE =\
    "/usr/share/doc/conntrack-tools-1.4.2/doc/stats/conntrackd.conf"
REPO_DIR = "/etc/yum.repos.d/CentOS-Base.repo"
TMP_REPO_DIR = "/tmp/repo"


def exit_with_error(err_msg):
    sys.stderr.write(err_msg)
    sys.exit(1)


def install_conntrack_tools(dom0_client):

    # check if conntrack service installed, or install it.
    try:
        dom0_client.ssh('ls /usr/sbin/conntrackd')
    except sshclient.SshExecCmdFailure:
        # prepare a temp yum repo and modify it
        cmd = "mkdir -p " + TMP_REPO_DIR + "; cp " + REPO_DIR + " " +\
              TMP_REPO_DIR + "; sed -i s/#baseurl=/baseurl=/g " + TMP_REPO_DIR
        dom0_client.ssh(cmd)
        # install conntrack tools using the temp repo
        cmd = "centos_ver=$(yum version nogroups |grep Installed | cut -d' ' "\
              "-f 2 | cut -d'/' -f 1 | cut -d'-' -f 1); yum install -y "\
              "-c " + TMP_REPO_DIR + " --enablerepo=base "\
              "--releasever=$centos_ver conntrack-tools"
        dom0_client.ssh(cmd)
        # backup conntrackd.conf after install conntrack-tools, use the one
        # with statistic mode
        cmd = "mv /etc/conntrackd/conntrackd.conf"\
              " /etc/conntrackd/conntrackd.conf.back; conntrack_conf=$(find "\
              "/usr/share/doc -name conntrackd.conf |grep stats); "\
              "cp $conntrack_conf /etc/conntrackd/conntrackd.conf"
        dom0_client.ssh(cmd)
        # restart service
        dom0_client.ssh("service conntrackd restart")


def enable_conntrack_service(dom0_client):
    # use conntrack statistic mode, so change conntrackd.conf
    return_pro = common_function.detailed_execute('find', '/usr/share/doc',
                                                  '-name', 'conntrackd.conf',
                                                  hold='true')
    return_pro, out, err = common_function.detailed_execute('grep',
                                                            'stats',
                                                            stdin=return_pro)

    try:
        dom0_client.ssh('ls /etc/conntrackd/conntrackd.conf.back')
    except sshclient.SshExecCmdFailure:
        # Only make conntrackd.conf.back if it doesn't exist
        try:
            dom0_client.ssh('mv /etc/conntrackd/conntrackd.conf '
                            '/etc/conntrackd/conntrackd.conf.back')
        except sshclient.SshExecCmdFailure:
            pass

    dom0_client.ssh('cp ' + contrackd_conf_dir +
                    ' /etc/conntrackd/conntrackd.conf')

    # Rotate log file for conntrack
    dom0_client.scp('/etc/logrotate.d/conntrackd',
                    '/etc/logrotate.d/conntrackd')

    # Restart conntrackd service
    dom0_client.ssh('service conntrackd restart')


if __name__ == '__main__':
    if len(sys.argv) != 5:
        exit_with_error("Wrong parameters input.")
    dom0_himn_ip, user_name, password, contrackd_conf_dir = sys.argv[1:]

    try:
        dom0_client = sshclient.SSHClient(dom0_himn_ip,
                                          user_name, password)
    except Exception:
        exit_with_error("Create connection failed, ip: %(dom0_himn_ip)s,"
                        " user_name: %(user_name)s" %
                        {'dom0_himn_ip': dom0_himn_ip,
                         'user_name': user_name})

    install_conntrack_tools(dom0_client)
    enable_conntrack_service(dom0_client, contrackd_conf_dir)
