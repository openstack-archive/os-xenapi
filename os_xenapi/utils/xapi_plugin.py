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

It contains the utilities relative to XAPI plugins."""

import os
import shutil
import sys
import tempfile

from os_xenapi.utils import common_function as fun
from os_xenapi.utils.sshclient import SSHClient


DOM0_PLUGIN_PATH = '/etc/xapi.d/plugins'
PKG_PLUGIN_PATH = 'os_xenapi/dom0/etc/xapi.d/plugins'
OS_XENAPI_PKG = 'os-xenapi'


def get_os_xenapi_dir(version=None):
    # Get os-xenapi's directory.
    # return (is_tmp_dir, os_xenapi_dir), where is_tmp_dir indicates
    # if the os_xenapi_dir is a temporary directory.
    is_tmp_dir = False
    os_xenapi_dir = None
    if version:
        # If version is specified, then download the specified package.
        # And unpack the package.
        temp_dir = tempfile.mkdtemp()
        fun.execute('pip', 'download', '--no-deps', '-d', temp_dir,
                    '%s==%s' % (OS_XENAPI_PKG, version))
        fun.execute('unzip', '-d', temp_dir, '%s/*.whl' % temp_dir)
        is_tmp_dir = True
        os_xenapi_dir = temp_dir
    else:
        # Check current installed os-xenapi package's location
        LOCATION_KEY = 'Location: '
        pkg_info = fun.execute('pip', 'show', OS_XENAPI_PKG).split('\n')
        for line in pkg_info:
            if line.startswith(LOCATION_KEY):
                os_xenapi_dir = line[len(LOCATION_KEY):]
                break
    return (is_tmp_dir, os_xenapi_dir)


def install_plugins_to_dom0(ssh_client, version=None):
    is_tmp_dir, dir = get_os_xenapi_dir(version)
    plugin_location = '%s/%s' % (dir, PKG_PLUGIN_PATH)
    try:
        for file in os.listdir(plugin_location):
            src_file = '%s/%s' % (plugin_location, file)
            dst_file = '%s/%s' % (DOM0_PLUGIN_PATH, file)
            ssh_client.scp(src_file, dst_file)
            ssh_client.ssh('chmod +x %s' % dst_file)
    finally:
        if is_tmp_dir:
            # delete the temp directory.
            shutil.rmtree(dir)


if __name__ == '__main__':
    # argv[1]: dom0's IP address
    # argv[2]: user name
    # argv[3]: user passwd
    # argv[4]: os-xenapi version (default None)
    ssh_client = SSHClient(sys.argv[1], sys.argv[2], sys.argv[3])
    version = None
    if len(sys.argv) > 4:
        version = sys.argv[4]
    install_plugins_to_dom0(ssh_client, version)
