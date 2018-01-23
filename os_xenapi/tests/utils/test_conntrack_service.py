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

from os_xenapi.tests import base
from os_xenapi.utils import conntrack_service


class XenapiConntrackServiceTestCase(base.TestCase):
    @mock.patch.object(os.path, 'dirname')
    def test_ensure_conntrack_packages(self, mock_dirname):
        client = mock.Mock()
        client.ssh.return_value = (0, '/tmp/domu_sh.fake', '')
        mock_dirname.return_value = '/fake_dir'
        ssh_expect_call = [mock.call("mkdir -p /tmp/domu_sh.fake"),
                           mock.call("chmod +x /tmp/domu_sh.fake/"
                                     "install_conntrack.sh"),
                           mock.call("/tmp/domu_sh.fake/install_conntrack.sh"),
                           mock.call("rm -rf /tmp/domu_sh.fake")]

        conntrack_service.ensure_conntrack_packages(client)
        client.ssh.assert_has_calls(ssh_expect_call)
        client.scp.assert_called_once_with(
            '/fake_dir/sh_tools/install_conntrack.sh',
            '/tmp/domu_sh.fake/install_conntrack.sh')

    @mock.patch.object(os.path, 'dirname')
    @mock.patch.object(conntrack_service, 'ensure_conntrack_packages')
    def test_enable_conntrack_service(self, mock_ensure_conntrack,
                                      mock_dir_name):
        client = mock.Mock()
        client.ssh.return_value = (0, '/tmp/domu_sh.fake', '')
        mock_dir_name.return_value = '/fake_dir'
        ssh_expect_call = [mock.call("mkdir -p /tmp/domu_sh.fake"),
                           mock.call("chmod +x /tmp/domu_sh.fake/"
                                     "enable_conntrack.sh"),
                           mock.call("/tmp/domu_sh.fake/enable_conntrack.sh"),
                           mock.call("rm -rf /tmp/domu_sh.fake")]

        conntrack_service.enable_conntrack_service(client)
        client.ssh.assert_has_calls(ssh_expect_call)
        client.scp.assert_called_once_with(
            '/fake_dir/sh_tools/enable_conntrack.sh',
            '/tmp/domu_sh.fake/enable_conntrack.sh')
        mock_ensure_conntrack.assert_called_once_with(client)
