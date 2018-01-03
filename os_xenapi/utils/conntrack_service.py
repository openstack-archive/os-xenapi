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

from os_xenapi.client import exception
from os_xenapi.utils import common_function
from os_xenapi.utils import sshclient


REPO_NAME = "CentOS-Base.repo"
REPO_PATH = "/etc/yum.repos.d/" + REPO_NAME
TMP_REPO_DIR = "/tmp/repo/"
TMP_REPO_PATH = TMP_REPO_DIR + REPO_NAME
PKG_NAME = "conntrack-tools"

common_function.setup_logging('conntrack_service')
LOG = logging.getLogger('conntrack_service')
LOG.setLevel(logging.DEBUG)


def exit_with_error(err_msg):
    sys.stderr.write(err_msg)
    sys.exit(1)


def ensure_conntrack_packages(dom0_client):
    # check if conntrack service installed, or install it.
    cmd = "if ! yum list installed " + PKG_NAME + "; then\n"  \
          "    mkdir -p " + TMP_REPO_DIR + ";\n"  \
          "    cp " + REPO_PATH + " " + TMP_REPO_DIR + ";\n" \
          "    sed -i s/#baseurl=/baseurl=/g " + TMP_REPO_PATH + ";\n" \
          "    centos_ver=$(yum version nogroups |grep Installed | cut -d' '"\
          "        -f 2 | cut -d'/' -f 1 | cut -d'-' -f 1);\n" \
          "    yum install -y -c " + TMP_REPO_PATH + " --enablerepo=base" \
          "        --releasever=$centos_ver " + PKG_NAME + ";\n" \
          "    rm -rf TMP_REPO_DIR;\n" \
          "fi\n"
    LOG.info("install conntrack service, cmd is %s", cmd)
    dom0_client.ssh(cmd)


def enable_conntrack_service(dom0_client):
    # use conntrack statistic mode, so change conntrackd.conf
    LOG.info("enable conntrack service")
    ensure_conntrack_packages(dom0_client)
    cmd = "yum info conntrack-tools | grep '^Version' | awk '{print $3}'"
    version, _ = dom0_client.ssh(cmd)
    version = version.strip('\r\n')
    cmd = "find /usr/share/doc/conntrack-tools-" + version + " -name " \
          "conntrackd.conf | grep stats"
    conf_pro_all, _ = dom0_client.ssh(cmd)
    if not conf_pro_all:
        raise exception.NotFound("Can not find configure file for conntrack "
                                 "service")
    conf_pro_all = conf_pro_all.strip()
    cmd = "if ! ls /etc/conntrackd/conntrackd.conf.back;  then\n" \
          "    cp -p /etc/conntrackd/conntrackd.conf" \
          "        /etc/conntrackd/conntrackd.conf.back\n" \
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
    dom0_client = sshclient.SSHClient(dom0_himn_ip, user_name, password)
    enable_conntrack_service(dom0_client)
