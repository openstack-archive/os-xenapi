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
import paramiko

from os_xenapi.tests import base
from os_xenapi.utils import sshclient


class fake_channel_file(object):
    def __init__(self, lines, channel=None):
        self.buf = iter(lines)
        self.channel = channel

    def __iter__(self):
        return self.buf


class SshClientTestCase(base.TestCase):
    @mock.patch.object(paramiko.SSHClient, 'set_missing_host_key_policy')
    @mock.patch.object(paramiko.SSHClient, 'connect')
    def test_init(self, mock_conn, mock_set):
        sshclient.SSHClient('ip', 'username', 'password')

        mock_conn.assert_called_with(
            'ip', username='username', password='password', pkey=None,
            key_filename=None, look_for_keys=False, allow_agent=False)

    @mock.patch.object(paramiko.SSHClient, 'set_missing_host_key_policy')
    @mock.patch.object(paramiko.SSHClient, 'connect')
    @mock.patch.object(paramiko.SSHClient, 'exec_command')
    def test_ssh(self, mock_exec, mock_conn, mock_set):
        mock_log = mock.Mock()
        mock_channel = mock.Mock()
        mock_exec.return_value = (fake_channel_file(['input']),
                                  fake_channel_file(['out_line1',
                                                     'out_line2'],
                                                    mock_channel),
                                  fake_channel_file(['err_line1',
                                                     'err_line2']))
        mock_channel.recv_exit_status.return_value = 0

        client = sshclient.SSHClient('ip', 'username', password='password',
                                     log=mock_log)
        return_code, out, err = client.ssh('fake_command')

        mock_log.debug.assert_called()
        mock_exec.assert_called()
        mock_log.info.assert_called_with('out_line1\nout_line2')
        mock_log.error.assert_called_with('err_line1\nerr_line2')
        mock_channel.recv_exit_status.assert_called_with()
        self.assertEqual(out, 'out_line1\nout_line2')
        self.assertEqual(err, 'err_line1\nerr_line2')

    @mock.patch.object(paramiko.SSHClient, 'set_missing_host_key_policy')
    @mock.patch.object(paramiko.SSHClient, 'connect')
    @mock.patch.object(paramiko.SSHClient, 'exec_command')
    def test_ssh_except(self, mock_exec, mock_conn, mock_set):
        mock_log = mock.Mock()
        mock_channel = mock.Mock()
        mock_exec.return_value = (fake_channel_file(['input']),
                                  fake_channel_file(['info'], mock_channel),
                                  fake_channel_file(['err']))
        mock_channel.recv_exit_status.return_value = -1

        client = sshclient.SSHClient('ip', 'username', password='password',
                                     log=mock_log)
        self.assertRaises(sshclient.SshExecCmdFailure,
                          client.ssh,
                          'fake_command')

    @mock.patch.object(paramiko.SSHClient, 'set_missing_host_key_policy')
    @mock.patch.object(paramiko.SSHClient, 'connect')
    @mock.patch.object(paramiko.SSHClient, 'exec_command')
    def test_ssh_allow_error_return(self, mock_exec, mock_conn, mock_set):
        mock_log = mock.Mock()
        mock_channel = mock.Mock()
        mock_exec.return_value = (fake_channel_file(['input']),
                                  fake_channel_file(['info'], mock_channel),
                                  fake_channel_file(['err']))
        mock_channel.recv_exit_status.return_value = 1

        client = sshclient.SSHClient('ip', 'username', password='password',
                                     log=mock_log)
        return_code, out, err = client.ssh('fake_command',
                                           allowed_return_codes=[0, 1])
        mock_exec.assert_called_once_with('fake_command', get_pty=True)
        mock_channel.recv_exit_status.assert_called_once()
        self.assertEqual(return_code, 1)

    @mock.patch.object(paramiko.SSHClient, 'set_missing_host_key_policy')
    @mock.patch.object(paramiko.SSHClient, 'connect')
    @mock.patch.object(paramiko.SSHClient, 'open_sftp')
    def test_scp(self, mock_open, mock_conn, mock_set):
        mock_log = mock.Mock()
        mock_sftp = mock.Mock()
        mock_open.return_value = mock_sftp

        client = sshclient.SSHClient('ip', 'username', password='password',

                                     log=mock_log)
        client.scp('source_file', 'dest_file')

        mock_log.info.assert_called()
        mock_sftp.put.assert_called_with('source_file', 'dest_file')
