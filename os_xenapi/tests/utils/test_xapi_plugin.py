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

from os_xenapi.tests import base
from os_xenapi.utils import common_function
from os_xenapi.utils import xapi_plugin


class XenapiPluginTestCase(base.TestCase):
    @mock.patch.object(common_function, 'execute')
    def test_get_plugins_location_with_version(self, mock_exec):
        version = '0.3.1'
        ret_val = xapi_plugin.get_plugins_location(version)

        expected_val = '%s/%s' % (xapi_plugin.DOWNLOAD_PATH,
                                  xapi_plugin.PKG_PLUGIN_PATH)
        self.assertEqual(ret_val, expected_val)
        self.assertEqual(4, mock_exec.call_count)

    @mock.patch.object(common_function, 'execute')
    def test_get_plugins_location_no_version(self, mock_exec):
        fake_loc = '/fake/install/loc'
        mock_exec.return_value = 'Location: %s\n' % fake_loc

        ret_val = xapi_plugin.get_plugins_location()

        expected_val = '%s/%s' % (fake_loc,
                                  xapi_plugin.PKG_PLUGIN_PATH)
        self.assertEqual(ret_val, expected_val)
        mock_exec.assert_called_with('pip', 'show',
                                     xapi_plugin.OS_XENAPI_PKG)

    @mock.patch.object(xapi_plugin, 'get_plugins_location')
    @mock.patch.object(common_function, 'execute')
    def test_install_plugins_to_dom0(self, mock_exec, mock_loc):
        ssh_client = mock.Mock()
        mock_loc.return_value = '/fake/path/to/plugin'
        mock_exec.return_value = 'file1\nfile2'

        xapi_plugin.install_plugins_to_dom0(ssh_client)

        dom0_path = xapi_plugin.DOM0_PLUGIN_PATH
        scp_expect = [mock.call('/fake/path/to/plugin/file1',
                                '%s/file1' % dom0_path),
                      mock.call('/fake/path/to/plugin/file2',
                                '%s/file2' % dom0_path)]
        ssh_expect = [mock.call('chmod +x %s/file1' % dom0_path),
                      mock.call('chmod +x %s/file2' % dom0_path)]
        self.assertEqual(scp_expect, ssh_client.scp.call_args_list)
        self.assertEqual(ssh_expect, ssh_client.ssh.call_args_list)
