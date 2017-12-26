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
"""XAPI plugin utils

It contains the utiles relative to XAPI plugins."""

import sys

from os_xenapi.utils import common_function as fun
from os_xenapi.utils.sshclient import SSHClient


DOM0_PLUGIN_PATH = '/etc/xapi.d/plugins'
PKG_PLUGIN_PATH = 'os_xenapi/dom0/etc/xapi.d/plugins'
OS_XENAPI_PKG = 'os-xenapi'
DOWNLOAD_PATH = '/tmp/xenapi'


def get_plugins_location(version=None):
    # get plugins's location
    if version:
        # If version is specified, then download the specified package.
        # And copy plugins from the download package.
        fun.execute('rm', '-rf', '%s' % DOWNLOAD_PATH)
        fun.execute('mkdir', '-p', '%s' % DOWNLOAD_PATH)
        fun.execute('pip', 'download', '--no-deps', '-d', DOWNLOAD_PATH,
                    '%s==%s' % (OS_XENAPI_PKG, version))
        fun.execute('unzip', '-d', DOWNLOAD_PATH,
                    '%s/*.whl' % DOWNLOAD_PATH)
        pkg_path = DOWNLOAD_PATH
    else:
        # Check current installed os-xenapi package's location
        LOCATION_KEY = 'Location: '
        pkg_info = fun.execute('pip', 'show', OS_XENAPI_PKG).split('\n')
        for line in pkg_info:
            if line.startswith(LOCATION_KEY):
                pkg_path = line[len(LOCATION_KEY):]

    return '%s/%s' % (pkg_path, PKG_PLUGIN_PATH)


def install_plugins_to_dom0(ssh_client, version=None):
    plugin_location = get_plugins_location(version)
    files = fun.execute('find', plugin_location, '-type', 'f',
                        '-printf', '%P\n').split('\n')
    for file in files:
        src_file = '%s/%s' % (plugin_location, file)
        dst_file = '%s/%s' % (DOM0_PLUGIN_PATH, file)
        ssh_client.scp(src_file, dst_file)
        ssh_client.ssh('chmod +x %s' % dst_file)


if __name__ == '__main__':
    # argv[1]: dom0's IP address
    # argv[2]: user name
    # argv[3]: user passwd
    ssh_client = SSHClient(sys.argv[1], sys.argv[2], sys.argv[3])
    install_plugins_to_dom0(ssh_client)
