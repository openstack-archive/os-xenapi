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

from os_xenapi.client import exception
from os_xenapi.utils import sshclient


REPO_NAME = "CentOS-Base.repo"
REPO_DIR = "/etc/yum.repos.d/" + REPO_NAME
TMP_REPO_DIR = "/tmp/repo/"
PKG_NAME = "conntrack-tools"


def exit_with_error(err_msg):
    sys.stderr.write(err_msg)
    sys.exit(1)


def ensure_conntrack_packages(dom0_client):
    # check if conntrack service installed, or install it.
    cmd = "if ! yum list installed " + PKG_NAME + "; then\n"  \
          "    mkdir -p " + TMP_REPO_DIR + ";\n"  \
          "    cp " + REPO_DIR + " " + TMP_REPO_DIR + ";\n" \
          "    sed -i s/#baseurl=/baseurl=/g " + TMP_REPO_DIR + REPO_NAME + \
          ";\n" \
          "    centos_ver=$(yum version nogroups |grep Installed | cut -d' ' "\
          "-f 2 | cut -d'/' -f 1 | cut -d'-' -f 1);\n" \
          "    yum install -y -c " + TMP_REPO_DIR + " --enablerepo=base " \
          "--releasever=$centos_ver " + PKG_NAME + ";\n" \
          "fi\n"
    dom0_client.ssh(cmd)


def enable_conntrack_service(dom0_client):
    # use conntrack statistic mode, so change conntrackd.conf
    ensure_conntrack_packages(dom0_client)
    conf_pro_all, _ = dom0_client.ssh('find /usr/share/doc -name '
                                      'conntrackd.conf | grep stats')
    conf_pro_all = conf_pro_all.strip()

    if not conf_pro_all:
        raise exception.NotFound("Can not find configure file for conntrack "
                                 "service")

    cmd = "if ! ls /etc/conntrackd/conntrackd.conf.back;  then\n" \
          "    cp -p /etc/conntrackd/conntrackd.conf " \
          "/etc/conntrackd/conntrackd.conf.back\n" \
          "fi\n"
    cmd += "cp " + conf_pro_all + " /etc/conntrackd/conntrackd.conf\n"
    dom0_client.ssh(cmd)
    # Rotate log file for conntrack
    cmd = "cat >/etc/logrotate.d/conntrackd <<EOF\n" \
          "/var/log/conntrackd*.log {\n" \
          "    daily\n" \
          "    maxsize 50M\n" \
          "    rotate 7\n" \
          "    copytruncate\n" \
          "    missingok\n" \
          "}\n" \
          "EOF"
    dom0_client.ssh(cmd)

    # Restart conntrackd service
    dom0_client.ssh('service conntrackd restart')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        exit_with_error("Wrong parameters input.")
    dom0_himn_ip, user_name, password = sys.argv[1:]

    try:
        dom0_client = sshclient.SSHClient(dom0_himn_ip,
                                          user_name, password)
    except Exception:
        exit_with_error("Create connection failed, ip: %(dom0_himn_ip)s,"
                        " user_name: %(user_name)s" %
                        {'dom0_himn_ip': dom0_himn_ip,
                         'user_name': user_name})

    enable_conntrack_service(dom0_client)
