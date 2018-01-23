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

from os_xenapi.client.exception import OsXenApiException
from os_xenapi.client.i18n import _
from os_xenapi.tests import base
from os_xenapi.utils import common_function


class SshExecCmdFailure(OsXenApiException):
    msg_fmt = _("scp failure")


class CommonUtilFuncTestCase(base.TestCase):
    def test_get_remote_hostname(self):
        mock_client = mock.Mock()
        out = ' \nFake_host_name\n '
        mock_client.ssh.return_value = (_, out, _)

        hostname = common_function.get_remote_hostname(mock_client)

        self.assertEqual(hostname, 'Fake_host_name')
        mock_client.ssh.assert_called_with('hostname')

    def test_get_host_ipv4s(self):
        mock_client = mock.Mock()
        out = u'xenbr0 10.71.64.118/20\n'
        out += 'xenapi 169.254.0.1/16\n'
        mock_client.ssh.return_value = (_, out, _)

        ipv4s = common_function.get_host_ipv4s(mock_client)

        expect = [
            {
                "address": "10.71.64.118",
                "broadcast": "10.71.79.255",
                "interface": "xenbr0",
                "netmask": "255.255.240.0",
                "network": "10.71.64.0"
            },
            {
                "address": "169.254.0.1",
                "broadcast": "169.254.255.255",
                "interface": "xenapi",
                "netmask": "255.255.0.0",
                "network": "169.254.0.0"
            }
        ]

        self.assertEqual(ipv4s, expect)
        mock_client.ssh.assert_called()

    @mock.patch.object(os.path, 'dirname')
    def test_scp_and_execute(self, mock_dirname):
        fake_util_dir = 'fake_util_dir'
        fake_tmp_sh_dir = 'fake_sh_dir'
        fake_script_name = 'fake_script_name'
        mock_dirname.return_value = fake_util_dir
        mock_client = mock.Mock()
        mock_client.ssh.return_value = (_, fake_tmp_sh_dir, _)
        fake_tmp_sh_path = fake_tmp_sh_dir + '/' + fake_script_name
        fake_sh_shell_dir = fake_util_dir + '/sh_tools/'

        expect_ssh_calls = [mock.call("mktemp -d /tmp/domu_sh.XXXXXX"),
                            mock.call("mkdir -p " + fake_tmp_sh_dir),
                            mock.call("chmod +x " + fake_tmp_sh_path),
                            mock.call(fake_tmp_sh_path),
                            mock.call("rm -rf " + fake_tmp_sh_dir)]

        common_function.scp_and_execute(mock_client, fake_script_name)
        mock_client.ssh.assert_has_calls(expect_ssh_calls)
        mock_client.scp.assert_called_once_with(
            fake_sh_shell_dir + fake_script_name, fake_tmp_sh_path)

    @mock.patch.object(os.path, 'dirname')
    def test_scp_and_execute_exception(self, mock_dirname):
        fake_util_dir = 'fake_util_dir'
        fake_tmp_sh_dir = 'fake_sh_dir'
        fake_script_name = 'fake_script_name'
        mock_dirname.return_value = fake_util_dir
        mock_client = mock.Mock()
        mock_client.ssh.return_value = (_, fake_tmp_sh_dir, _)
        fake_tmp_sh_path = fake_tmp_sh_dir + '/' + fake_script_name
        fake_sh_shell_dir = fake_util_dir + '/sh_tools/'
        mock_client.scp.side_effect = [SshExecCmdFailure()]

        expect_ssh_calls = [mock.call("mktemp -d /tmp/domu_sh.XXXXXX"),
                            mock.call("mkdir -p " + fake_tmp_sh_dir),
                            mock.call("rm -rf " + fake_tmp_sh_dir)]

        self.assertRaises(SshExecCmdFailure,
                          common_function.scp_and_execute,
                          mock_client, fake_script_name)
        mock_client.ssh.assert_has_calls(expect_ssh_calls)
        mock_client.scp.assert_called_once_with(
            fake_sh_shell_dir + fake_script_name, fake_tmp_sh_path)
