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
from os_xenapi.client import exception
from os_xenapi.client.i18n import _
from os_xenapi.tests import base
from os_xenapi.utils import common_function
from os_xenapi.utils import himn
from os_xenapi.utils import iptables
from os_xenapi.utils import sshclient


class fake_client_exception(exception.OsXenApiException):
    msg_fmt = _("Failed to connect to server")


class XenapiIptableTestCase(base.TestCase):
    @mock.patch.object(iptables, 'configure_himn_forwards')
    @mock.patch.object(iptables, 'configure_dom0_iptables')
    def test_config_iptables(self, mock_conf_dom0, mock_himn_forwards):
        client = mock.Mock()
        client.ip = 'fake_ip'

        iptables.config_iptables(client, 'fake_interface')
        mock_himn_forwards.assert_called_once_with('fake_interface', 'fake_ip')
        mock_conf_dom0.assert_called_once_with(client)

    @mock.patch.object(iptables, 'configure_himn_forwards')
    @mock.patch.object(iptables, 'configure_dom0_iptables')
    def test_config_iptables_without_forwards(self, mock_conf_dom0,
                                              mock_himn_forwards):
        client = mock.Mock()
        client.ip = 'fake_ip'

        iptables.config_iptables(client, None)
        mock_himn_forwards.assert_not_called()
        mock_conf_dom0.assert_called_once_with(client)

    def test_configure_dom0_iptables(self):
        client = mock.Mock()
        client.ssh.side_effect = [sshclient.SshExecCmdFailure(
                                  command="fake_cmd",
                                  stdout="fake_out",
                                  stderr="fake_err"),
                                  None,
                                  None,
                                  sshclient.SshExecCmdFailure(
                                  command="fake_cmd",
                                  stdout="fake_out",
                                  stderr="fake_err"),
                                  None,
                                  sshclient.SshExecCmdFailure(
                                  command="fake_cmd",
                                  stdout="fake_out",
                                  stderr="fake_err"),
                                  None,
                                  None]
        xs_chain = 'XenServer-Neutron-INPUT'
        expect_call1 = mock.call('iptables -t filter -L %s' % xs_chain)
        expect_call2 = mock.call('iptables -t filter --new %s' % xs_chain)
        expect_call3 = mock.call('iptables -t filter -I INPUT -j %s'
                                 % xs_chain)
        expect_call4 = mock.call('iptables -t filter -C %s -p tcp -m '
                                 'tcp --dport 6640 -j ACCEPT' % xs_chain)
        expect_call5 = mock.call('iptables -t filter -I %s -p tcp -m '
                                 'tcp --dport 6640 -j ACCEPT' % xs_chain)
        expect_call6 = mock.call('iptables -t filter -C %s -p udp -m '
                                 'multiport --dport 4789 -j ACCEPT' % xs_chain)
        expect_call7 = mock.call('iptables -t filter -I %s -p udp -m '
                                 'multiport --dport 4789 -j ACCEPT' % xs_chain)
        expect_call8 = mock.call("service iptables save")
        expect_calls = [expect_call1, expect_call2, expect_call3, expect_call4,
                        expect_call5, expect_call6, expect_call7, expect_call8]
        iptables.configure_dom0_iptables(client)
        client.ssh.assert_has_calls(expect_calls)

    @mock.patch.object(himn, 'get_local_himn_eth')
    @mock.patch.object(common_function, 'execute')
    def test_configure_himn_forwards(self, mock_execute, mock_get_eth):
        mock_get_eth.return_value = 'fake_eth'
        fack_end_point = ['br-storage', 'br-mgmt']
        mock_execute.side_effect = [None,
                                    None,
                                    exception.ExecuteCommandFailed('fake_cmd'),
                                    None,
                                    exception.ExecuteCommandFailed('fake_cmd'),
                                    None,
                                    exception.ExecuteCommandFailed('fake_cmd'),
                                    None,
                                    exception.ExecuteCommandFailed('fake_cmd'),
                                    None,
                                    exception.ExecuteCommandFailed('fake_cmd'),
                                    None,
                                    exception.ExecuteCommandFailed('fake_cmd'),
                                    None,
                                    exception.ExecuteCommandFailed('fake_cmd'),
                                    None,
                                    None,
                                    None,
                                    None]

        expect_call1 = mock.call(
            'sed',
            '-i', 's/.*net\.ipv4\.ip_forward.*=.*/net.ipv4.ip_forward=1/g',
            '/etc/sysctl.conf')
        expect_call2 = mock.call('sysctl', 'net.ipv4.ip_forward=1')

        expect_call3 = mock.call('iptables', '-t', 'nat', '-C', 'POSTROUTING',
                                 '-o', fack_end_point[0], '-j', 'MASQUERADE')
        expect_call4 = mock.call('iptables', '-t', 'nat', '-I', 'POSTROUTING',
                                 '-o', fack_end_point[0], '-j', 'MASQUERADE')

        expect_call5 = mock.call('iptables', '-t', 'nat', '-C', 'POSTROUTING',
                                 '-o', fack_end_point[1], '-j', 'MASQUERADE')
        expect_call6 = mock.call('iptables', '-t', 'nat', '-I', 'POSTROUTING',
                                 '-o', fack_end_point[1], '-j', 'MASQUERADE')

        expect_call7 = mock.call('iptables', '-t', 'filter', '-C', 'FORWARD',
                                 '-i', fack_end_point[0], '-o', 'fake_eth',
                                 '-m', 'state', '--state',
                                 'RELATED,ESTABLISHED', '-j', 'ACCEPT')
        expect_call8 = mock.call('iptables', '-t', 'filter', '-I', 'FORWARD',
                                 '-i', fack_end_point[0], '-o', 'fake_eth',
                                 '-m', 'state', '--state',
                                 'RELATED,ESTABLISHED', '-j', 'ACCEPT')

        expect_call9 = mock.call('iptables', '-t', 'filter', '-C', 'FORWARD',
                                 '-i', fack_end_point[1], '-o', 'fake_eth',
                                 '-m', 'state', '--state',
                                 'RELATED,ESTABLISHED', '-j', 'ACCEPT')
        expect_call10 = mock.call('iptables', '-t', 'filter', '-I', 'FORWARD',
                                  '-i', fack_end_point[1], '-o', 'fake_eth',
                                  '-m', 'state', '--state',
                                  'RELATED,ESTABLISHED', '-j', 'ACCEPT')

        expect_call11 = mock.call('iptables', '-t', 'filter', '-C', 'FORWARD',
                                  '-i', 'fake_eth', '-o', fack_end_point[0],
                                  '-j', 'ACCEPT')
        expect_call12 = mock.call('iptables', '-t', 'filter', '-I', 'FORWARD',
                                  '-i', 'fake_eth', '-o', fack_end_point[0],
                                  '-j', 'ACCEPT')

        expect_call13 = mock.call('iptables', '-t', 'filter', '-C', 'FORWARD',
                                  '-i', 'fake_eth', '-o', fack_end_point[1],
                                  '-j', 'ACCEPT')
        expect_call14 = mock.call('iptables', '-t', 'filter', '-I', 'FORWARD',
                                  '-i', 'fake_eth', '-o', fack_end_point[1],
                                  '-j', 'ACCEPT')

        expect_call15 = mock.call('iptables', '-t', 'filter', '-C', 'INPUT',
                                  '-i', 'fake_eth', '-j', 'ACCEPT')
        expect_call16 = mock.call('iptables', '-t', 'filter', '-I', 'INPUT',
                                  '-i', 'fake_eth', '-j', 'ACCEPT')

        expect_call17 = mock.call('iptables', '-t', 'filter', '-S', 'FORWARD')
        expect_call18 = mock.call('iptables', '-t', 'nat', '-S', 'POSTROUTING')

        expect_calls = [expect_call1, expect_call2,
                        expect_call3, expect_call4,
                        expect_call7, expect_call8,
                        expect_call11, expect_call12,
                        expect_call5, expect_call6,
                        expect_call9, expect_call10,
                        expect_call13, expect_call14,
                        expect_call15, expect_call16,
                        expect_call17, expect_call18]
        iptables.configure_himn_forwards(fack_end_point, 'fake_dom0_himn_ip')
        mock_get_eth.assert_called_once_with('fake_dom0_himn_ip')
        mock_execute.assert_has_calls(expect_calls)

    @mock.patch.object(himn, 'get_local_himn_eth')
    @mock.patch.object(common_function, 'execute')
    def test_configure_himn_forwards_no_eth_exc(self, mock_execute,
                                                mock_get_eth):
        mock_get_eth.return_value = None
        self.assertRaises(exception.NoNetworkInterfaceInSameSegment,
                          iptables.configure_himn_forwards,
                          'fake_end_point', 'fake_dom0_himn_ip')

    @mock.patch.object(common_function, 'execute')
    def test_execute_local_iptables_cmd(self, mock_execute):
        fake_rule_spec = 'fake_rule'
        mock_execute.return_value = 'success'

        execute_result = iptables.execute_iptables_cmd('fake_table',
                                                       'fake_action',
                                                       'fake_chain',
                                                       fake_rule_spec)
        self.assertTrue(execute_result)
        mock_execute.assert_called_once_with('iptables', '-t', 'fake_table',
                                             'fake_action', 'fake_chain',
                                             fake_rule_spec)

    @mock.patch.object(common_function, 'execute')
    def test_execute_local_iptables_cmd_failed(self, mock_execute):
        fake_rule_spec = 'fake_rule'
        mock_execute.side_effect = [exception.ExecuteCommandFailed('fake_cmd')]

        self.assertRaises(exception.ExecuteCommandFailed,
                          iptables.execute_iptables_cmd,
                          'fake_table', 'fake_action',
                          'fake_chain', fake_rule_spec)

        mock_execute.assert_called_once_with('iptables', '-t', 'fake_table',
                                             'fake_action', 'fake_chain',
                                             fake_rule_spec)

    @mock.patch.object(common_function, 'execute')
    def test_execute_local_iptables_cmd_expect_failed(self, mock_execute):
        fake_rule_spec = 'fake_rule'
        mock_execute.side_effect = [exception.ExecuteCommandFailed('fake_cmd')]

        execute_result = iptables.execute_iptables_cmd('fake_table',
                                                       'fake_action',
                                                       'fake_chain',
                                                       fake_rule_spec,
                                                       None,
                                                       True)
        self.assertFalse(execute_result)
        mock_execute.assert_called_once_with('iptables', '-t', 'fake_table',
                                             'fake_action', 'fake_chain',
                                             fake_rule_spec)

    @mock.patch.object(common_function, 'execute')
    def test_execute_local_iptables_cmd_no_rule_spec(self, mock_execute):
        mock_execute.return_value = 'success'

        execute_result = iptables.execute_iptables_cmd('fake_table',
                                                       'fake_action',
                                                       'fake_chain',
                                                       None)
        self.assertTrue(execute_result)
        mock_execute.assert_called_once_with('iptables', '-t', 'fake_table',
                                             'fake_action', 'fake_chain')

    def test_execute_remote_iptables_cmd(self):
        fake_client = mock.Mock()
        fake_rule_spec = 'fake_rule'
        fake_client.ssh.return_value = 'success'

        execute_result = iptables.execute_iptables_cmd('fake_table',
                                                       'fake_action',
                                                       'fake_chain',
                                                       fake_rule_spec,
                                                       fake_client)
        self.assertTrue(execute_result)
        fake_client.ssh.assert_called_once_with('iptables -t fake_table ' +
                                                'fake_action fake_chain ' +
                                                fake_rule_spec)

    def test_execute_remote_iptables_cmd_failed(self):
        fake_client = mock.Mock()
        fake_rule_spec = 'fake_rule'
        fake_client.ssh.side_effect = [sshclient.SshExecCmdFailure(
                                       command="fake_cmd",
                                       stdout="fake_out",
                                       stderr="fake_err")]

        self.assertRaises(sshclient.SshExecCmdFailure,
                          iptables.execute_iptables_cmd,
                          'fake_table', 'fake_action',
                          'fake_chain', fake_rule_spec,
                          fake_client)

        fake_client.ssh.assert_called_once_with('iptables -t fake_table ' +
                                                'fake_action fake_chain ' +
                                                fake_rule_spec)

    def test_execute_remote_iptables_cmd_expect_failed(self):
        fake_client = mock.Mock()
        fake_rule_spec = 'fake_rule'
        fake_client.ssh.side_effect = [sshclient.SshExecCmdFailure(
                                       command="fake_cmd",
                                       stdout="fake_out",
                                       stderr="fake_err")]

        execute_result = iptables.execute_iptables_cmd('fake_table',
                                                       'fake_action',
                                                       'fake_chain',
                                                       fake_rule_spec,
                                                       fake_client,
                                                       True)
        self.assertFalse(execute_result)
        fake_client.ssh.assert_called_once_with('iptables -t fake_table ' +
                                                'fake_action fake_chain ' +
                                                fake_rule_spec)

    def test_execute_remote_iptables_cmd_no_rule_spec(self):
        fake_client = mock.Mock()
        fake_client.ssh.return_value = 'success'

        execute_result = iptables.execute_iptables_cmd('fake_table',
                                                       'fake_action',
                                                       'fake_chain',
                                                       None,
                                                       fake_client)
        self.assertTrue(execute_result)
        fake_client.ssh.assert_called_once_with("iptables -t fake_table "
                                                "fake_action fake_chain")
