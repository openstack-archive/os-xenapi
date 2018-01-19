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


class CommonUtilFuncTestCase(base.TestCase):
    def test_get_remote_hostname(self):
        mock_client = mock.Mock()
        out = ' \nFake_host_name\n '
        err = ''
        mock_client.ssh.return_value = (out, err)

        hostname = common_function.get_remote_hostname(mock_client)

        self.assertEqual(hostname, 'Fake_host_name')
        mock_client.ssh.assert_called_with('hostname')

    def test_get_host_ipv4s(self):
        mock_client = mock.Mock()
        out = u'xenbr0 10.71.64.118/20\n'
        out += 'xenapi 169.254.0.1/16\n'
        err = ''
        mock_client.ssh.return_value = (out, err)

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

    def test_get_vm_vifs(self):
        mock_client = mock.Mock()
        vm_uuid = '9eeeea9f-de18-f101-fcc2-ae7366b540f2'
        vif_list_data = u'0\r\n\n1\r\n'

        vif_0_data = u'vif-id = "0"\r\n\n'
        vif_0_data += u'mac = "9a:77:18:20:cf:14"\r\n\n'
        vif_0_data += u'bridge = "xapi1"\r\n'

        vif_1_data = u'vif-id = "1"\r\n\n'
        vif_1_data += u'mac = "02:e3:69:a6:7b:b8"\r\n\n'
        vif_1_data += u'bridge = "xapi0"\r\n'

        mock_client.ssh.side_effect = [(vif_list_data, ''),  # xenstore-list
                                       (vif_0_data, ''),  # xenstore-ls - vif 0
                                       (vif_1_data, ''),  # xenstore-ls - vif 1
                                       ]

        expect = [{u'bridge': u'xapi1',
                   u'mac': u'9a:77:18:20:cf:14',
                   u'vif-id': u'0'},
                  {u'bridge': u'xapi0',
                   u'mac': u'02:e3:69:a6:7b:b8',
                   u'vif-id': u'1'}]
        vifs = common_function.get_vm_vifs(mock_client, vm_uuid)
        self.assertEqual(vifs, expect)

    @mock.patch.object(common_function.netifaces, 'ifaddresses')
    @mock.patch.object(common_function.netifaces, 'interfaces')
    @mock.patch.object(common_function, 'execute')
    @mock.patch.object(common_function, 'get_vm_vifs')
    def test_get_domu_vifs_by_eth(self, mock_get, mock_exec,
                                  mock_if, mock_ifaddr):
        mock_client = mock.Mock()
        vm_uuid = '9eeeea9f-de18-f101-fcc2-ae7366b540f2'
        mock_exec.return_value = '/vm/%s' % vm_uuid
        vif_0 = {u'vif-id': u'0',
                 u'bridge': u'xapi1',
                 u'mac': u'9a:77:18:20:cf:14'}
        vif_1 = {u'vif-id': u'1',
                 u'bridge': u'xapi0',
                 u'mac': u'02:e3:69:a6:7b:b8'}

        mock_get.return_value = [vif_0, vif_1]
        mock_if.return_value = ['eth0', 'eth1']
        AF_LINK = common_function.netifaces.AF_LINK
        mock_ifaddr.side_effect = [
            {AF_LINK: [{u'addr': u'9a:77:18:20:cf:14'}]},
            {AF_LINK: [{u'addr': u'02:e3:69:a6:7b:b8'}]}]

        vifs_by_eth = common_function.get_domu_vifs_by_eth(mock_client)

        expect = {'eth0': vif_0,
                  'eth1': vif_1}
        self.assertEqual(vifs_by_eth, expect)
        mock_exec.assert_called_with('xenstore-read', 'vm')
        mock_get.assert_called_with(mock_client, vm_uuid)
        mock_if.assert_called_with()
        self.assertEqual(mock_ifaddr.call_args_list,
                         [mock.call('eth0'), mock.call('eth1')])
