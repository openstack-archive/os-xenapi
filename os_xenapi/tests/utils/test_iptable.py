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
from os_xenapi.tests import base
from os_xenapi.utils import common_function
from os_xenapi.utils import himn
from os_xenapi.utils import iptables
from os_xenapi.utils import sshclient


class XenapiIptableTestCase(base.TestCase):
    @mock.patch.object(sshclient, 'SSHClient')
    @mock.patch.object(iptables, 'execute_dom0_iptables_commands')
    def test_configure_dom0_iptables(self, fake_execute, fake_client):
        client = mock.Mock()
        fake_client.return_value = client
        xs_chain = 'XenServer-Neutron-INPUT'
        expect_cmd1 = ('iptables -t filter -L %s;' % xs_chain,
                       'iptables -t filter --new %s;' % xs_chain,
                       'iptables -t filter -I INPUT -j %s' % xs_chain)
        expect_cmd2 = ('iptables -t filter -C %s -p tcp -m tcp --dport 6640 '
                       '-j ACCEPT;' % xs_chain,
                       'iptables -t filter -I %s -p tcp --dport 6640 -j '
                       'ACCEPT' % xs_chain)
        expect_cmd3 = ('iptables -t filter -C %s -p udp -m multiport '
                       '--dports 4789 -j ACCEPT;' % xs_chain,
                       'iptables -t filter -I %s -p udp -m multiport --dport '
                       '4789 -j ACCEPT' % xs_chain)
        expect_calls = [mock.call(client, expect_cmd1),
                        mock.call(client, expect_cmd2),
                        mock.call(client, expect_cmd3)]
        iptables.configure_dom0_iptables('fake_dom0_himn_ip', 'fake_user_name',
                                         'fake_password')
        fake_execute.assert_has_calls(expect_calls)

    @mock.patch.object(sshclient, 'SSHClient')
    def test_configure_dom0_iptables_invalid_session(self, fake_client):
        fake_client.return_value = None

        self.assertRaises(exception.SSHClientInvalid,
                          iptables.configure_dom0_iptables,
                          'fake_dom0_himn_ip', 'fake_user_name',
                          'fake_password')

    @mock.patch.object(himn, 'get_local_himn_eth')
    @mock.patch.object(common_function, 'execute')
    def test_configure_himn_forwards(self, mock_excute, mock_get_eth):
        mock_get_eth.return_value = 'fake_eth'
        fack_end_point = ['br-storage', 'br-mgmt']
        expect_call1 = mock.call('iptables', '-t', 'nat', '-A', 'POSTROUTING',
                                 '-o', fack_end_point[0], '-j', 'MASQUERADE')
        expect_call2 = mock.call('iptables', '-t', 'nat', '-A', 'POSTROUTING',
                                 '-o', fack_end_point[1], '-j', 'MASQUERADE')
        expect_call3 = mock.call('iptables', '-A', 'FORWARD',
                                 '-i', fack_end_point[0], '-o', 'fake_eth',
                                 '-m', 'state', '--state',
                                 'RELATED,ESTABLISHED', '-j', 'ACCEPT')
        expect_call4 = mock.call('iptables', '-A', 'FORWARD',
                                 '-i', fack_end_point[1], '-o', 'fake_eth',
                                 '-m', 'state', '--state',
                                 'RELATED,ESTABLISHED', '-j', 'ACCEPT')
        expect_call5 = mock.call('iptables', '-A', 'FORWARD',
                                 '-i', 'fake_eth', '-o', fack_end_point[0],
                                 '-j', 'ACCEPT')
        expect_call6 = mock.call('iptables', '-A', 'FORWARD',
                                 '-i', 'fake_eth', '-o', fack_end_point[1],
                                 '-j', 'ACCEPT')
        expect_call7 = mock.call('iptables', '-A', 'INPUT', '-i', 'fake_eth',
                                 '-j', 'ACCEPT')
        expect_call8 = mock.call('iptables', '-t', 'filter', '-S', 'FORWARD')
        expect_call9 = mock.call('iptables', '-t', 'nat', '-S', 'POSTROUTING')

        expect_calls = [expect_call1, expect_call3,
                        expect_call5, expect_call7,
                        expect_call8, expect_call9,
                        expect_call2, expect_call4,
                        expect_call6, expect_call7,
                        expect_call8, expect_call9]
        iptables.configure_himn_forwards(fack_end_point, 'fake_dom0_himn_ip')
        mock_get_eth.assert_called_once_with('fake_dom0_himn_ip')
        mock_excute.assert_has_calls(expect_calls)

    @mock.patch.object(himn, 'get_local_himn_eth')
    @mock.patch.object(common_function, 'execute')
    def test_configure_himn_forwards_no_eth_exc(self, mock_excute,
                                                mock_get_eth):
        mock_get_eth.return_value = None
        self.assertRaises(exception.NoNetworkInterfaceWithIp,
                          iptables.configure_himn_forwards,
                          'fake_end_point', 'fake_dom0_himn_ip')
