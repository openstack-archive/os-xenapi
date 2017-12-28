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

import ipaddress
import netifaces

import mock
from os_xenapi.client import exception
from os_xenapi.tests import base
from os_xenapi.utils import common_function
from os_xenapi.utils import himn


class XenapiHIMNTestCase(base.TestCase):
    @mock.patch.object(himn, 'get_local_himn_eth_via_ip')
    @mock.patch.object(himn, 'get_local_himn_eth_via_xenstore')
    @mock.patch.object(himn, 'persist_eth_cfg')
    def test_config_himn_with_ip_eth(self, mock_persist_eth,
                                     mock_get_eth_xstore,
                                     mock_get_eth_ip):
        fake_eth = 'fake_eth'
        mock_get_eth_ip.return_value = fake_eth
        fake_himn_ip = 'fake_himn_ip'

        himn.config_himn(fake_himn_ip)
        mock_get_eth_ip.assert_called_once_with(fake_himn_ip)
        mock_persist_eth.assert_called_once_with(fake_eth)
        mock_get_eth_xstore.assert_not_called()

    @mock.patch.object(himn, 'get_local_himn_eth_via_ip')
    @mock.patch.object(himn, 'get_local_himn_eth_via_xenstore')
    @mock.patch.object(himn, 'persist_eth_cfg')
    @mock.patch.object(common_function, 'execute')
    def test_config_himn_with_xenstore_eth(self, mock_execute,
                                           mock_persist_eth,
                                           mock_get_eth_xstore,
                                           mock_get_eth_ip):
        fake_eth = 'fake_eth'
        mock_get_eth_ip.return_value = None
        mock_get_eth_xstore.return_value = fake_eth
        fake_himn_ip = 'fake_himn_ip'

        himn.config_himn(fake_himn_ip)
        mock_get_eth_ip.assert_called_once_with(fake_himn_ip)
        mock_persist_eth.assert_called_once_with(fake_eth)
        mock_get_eth_xstore.assert_called_once()

    @mock.patch.object(himn, 'get_local_himn_eth_via_ip')
    @mock.patch.object(himn, 'get_local_himn_eth_via_xenstore')
    @mock.patch.object(himn, 'persist_eth_cfg')
    def test_config_himn_exception_no_eth(self, mock_persist_eth,
                                          mock_get_eth_xstore,
                                          mock_get_eth_ip):
        mock_get_eth_ip.return_value = None
        mock_get_eth_xstore.return_value = None
        fake_himn_ip = 'fake_himn_ip'

        self.assertRaises(exception.NoNetworkInterfaceWithIp,
                          himn.config_himn,
                          fake_himn_ip)
        mock_get_eth_ip.assert_called_once_with(fake_himn_ip)
        mock_persist_eth.assert_not_called()
        mock_get_eth_xstore.assert_called_once()

    @mock.patch.object(common_function, 'execute')
    @mock.patch.object(netifaces, 'interfaces')
    @mock.patch.object(common_function, 'get_eth_mac')
    def test_get_local_himn_eth_via_xenstore(self, mock_get_eth_mac,
                                             mock_nf_interface,
                                             mock_execute):
        fake_domid = 'fake_domid'
        fake_himn_mac = 'fake_himn_mac'
        mock_execute.side_effect = [fake_domid, fake_himn_mac]
        expect_call1 = mock.call('xenstore-read', 'domid')
        expect_call2 = mock.call(
            'xenstore-read',
            '/local/domain/%s/vm-data/himn_mac' % fake_domid)
        expect_eth = 'fake_hinm_eth'
        mock_nf_interface.return_value = ['fake_eth1',
                                          expect_eth,
                                          'fake_eth3']
        mock_get_eth_mac.side_effect = ['fake_mac1',
                                        fake_himn_mac,
                                        'fake_mac3']

        return_eth = himn.get_local_himn_eth_via_xenstore()
        self.assertEqual(return_eth, expect_eth)
        mock_execute.assert_has_calls([expect_call1, expect_call2])
        mock_nf_interface.assert_called()
        mock_get_eth_mac.assert_has_calls([mock.call('fake_eth1'),
                                           mock.call(expect_eth),
                                           mock.call('fake_eth3')])

    @mock.patch.object(common_function, 'execute')
    @mock.patch.object(netifaces, 'interfaces')
    @mock.patch.object(common_function, 'get_eth_mac')
    def test_exception_more_than_one_eth(self, mock_get_eth_mac,
                                         mock_nf_interface,
                                         mock_execute):
        fake_domid = 'fake_domid'
        fake_himn_mac = 'fake_himn_mac'
        mock_execute.side_effect = [fake_domid, fake_himn_mac]
        expect_call1 = mock.call('xenstore-read', 'domid')
        expect_call2 = mock.call(
            'xenstore-read',
            '/local/domain/%s/vm-data/himn_mac' % fake_domid)
        expect_eth = 'fake_hinm_eth'
        mock_nf_interface.return_value = ['fake_eth1',
                                          expect_eth,
                                          'fake_eth3']
        mock_get_eth_mac.side_effect = ['fake_mac1',
                                        fake_himn_mac,
                                        fake_himn_mac]

        self.assertRaises(exception.NoNetworkInterfaceWithMac,
                          himn.get_local_himn_eth_via_xenstore)
        mock_execute.assert_has_calls([expect_call1, expect_call2])
        mock_nf_interface.assert_called()
        mock_get_eth_mac.assert_has_calls([mock.call('fake_eth1'),
                                           mock.call(expect_eth),
                                           mock.call('fake_eth3')])

    @mock.patch.object(netifaces, 'interfaces')
    @mock.patch.object(ipaddress, 'ip_network')
    @mock.patch.object(ipaddress, 'ip_address')
    def test_get_local_himn_eth_via_ip(self, mock_id_ipadress,
                                       mock_id_ip_network,
                                       mock_nf_interface):
        # TODO(naichuans): need to confirm if the function could work on
        # python2.7
        pass
