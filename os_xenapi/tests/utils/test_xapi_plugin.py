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

import mock
import os
import shutil
import tempfile

from os_xenapi.tests import base
from os_xenapi.utils import common_function
from os_xenapi.utils import xapi_plugin


class XenapiPluginTestCase(base.TestCase):
    @mock.patch.object(tempfile, 'mkdtemp',
                       return_value='/tmp/tmp1VyeJn')
    @mock.patch.object(common_function, 'execute')
    def test_get_os_xenapi_dir_with_version(self, mock_exec, mock_tmp):
        VERSION = '0.3.1'
        is_tmp, dir = xapi_plugin.get_os_xenapi_dir(VERSION)

        self.assertEqual(2, mock_exec.call_count)
        self.assertEqual(dir, '/tmp/tmp1VyeJn')
        self.assertEqual(is_tmp, True)

    @mock.patch.object(tempfile, 'mkdtemp')
    @mock.patch.object(common_function, 'execute')
    def test_get_os_xenapi_dir_no_version(self, mock_exec, mock_tmp):
        fake_loc = '/fake/install/loc'
        mock_exec.return_value = 'Location: %s\n' % fake_loc

        is_tmp, dir = xapi_plugin.get_os_xenapi_dir()

        self.assertEqual(dir, fake_loc)
        self.assertEqual(is_tmp, False)
        mock_exec.assert_called_with('pip', 'show',
                                     xapi_plugin.OS_XENAPI_PKG)
        mock_tmp.assert_not_called()

    @mock.patch.object(xapi_plugin, 'get_os_xenapi_dir')
    @mock.patch.object(os, 'listdir')
    @mock.patch.object(shutil, 'rmtree')
    def test_install_plugins_to_dom0_no_version(self, mock_rm, mock_dir,
                                                mock_get):
        FAKE_PKG_PATH = '/fake/pkg/path'
        ssh_client = mock.Mock()
        mock_get.return_value = (False, FAKE_PKG_PATH)
        mock_dir.return_value = ['file1', 'file2']

        xapi_plugin.install_plugins_to_dom0(ssh_client)

        dom0_path = xapi_plugin.DOM0_PLUGIN_PATH
        local_path = '%s/%s' % (FAKE_PKG_PATH,
                                xapi_plugin.PKG_PLUGIN_PATH)
        scp_expect = [mock.call('%s/file1' % local_path,
                                '%s/file1' % dom0_path),
                      mock.call('%s/file2' % local_path,
                                '%s/file2' % dom0_path)]
        ssh_expect = [mock.call('chmod +x %s/file1' % dom0_path),
                      mock.call('chmod +x %s/file2' % dom0_path)]
        self.assertEqual(scp_expect, ssh_client.scp.call_args_list)
        self.assertEqual(ssh_expect, ssh_client.ssh.call_args_list)
        # Shouldn't invoke mock_rm to remove the package dir.
        mock_rm.assert_not_called()

    @mock.patch.object(xapi_plugin, 'get_os_xenapi_dir')
    @mock.patch.object(os, 'listdir')
    @mock.patch.object(shutil, 'rmtree')
    def test_install_plugins_to_dom0_with_version(self, mock_rm, mock_dir,
                                                  mock_get):
        VERSION = '0.3.1'
        FAKE_PKG_PATH = '/tmp/tmp1VyeJn'
        ssh_client = mock.Mock()
        mock_get.return_value = (True, FAKE_PKG_PATH)
        mock_dir.return_value = ['file1', 'file2']

        xapi_plugin.install_plugins_to_dom0(ssh_client, VERSION)

        dom0_path = xapi_plugin.DOM0_PLUGIN_PATH
        local_path = '%s/%s' % (FAKE_PKG_PATH,
                                xapi_plugin.PKG_PLUGIN_PATH)
        scp_expect = [mock.call('%s/file1' % local_path,
                                '%s/file1' % dom0_path),
                      mock.call('%s/file2' % local_path,
                                '%s/file2' % dom0_path)]
        ssh_expect = [mock.call('chmod +x %s/file1' % dom0_path),
                      mock.call('chmod +x %s/file2' % dom0_path)]
        self.assertEqual(scp_expect, ssh_client.scp.call_args_list)
        self.assertEqual(ssh_expect, ssh_client.ssh.call_args_list)
        # Should invoke mock_rm to remove the package dir.
        mock_rm.assert_called_with(FAKE_PKG_PATH)
