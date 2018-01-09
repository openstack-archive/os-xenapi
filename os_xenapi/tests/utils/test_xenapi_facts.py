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
import netifaces

from os_xenapi.tests import base
from os_xenapi.utils import common_function
from os_xenapi.utils import himn
from os_xenapi.utils import xenapi_facts


class XenapiFactsTestCase(base.TestCase):
    @mock.patch.object(common_function, 'get_host_ipv4s')
    @mock.patch.object(common_function, 'get_remote_hostname')
    @mock.patch.object(himn, 'get_local_himn_eth')
    @mock.patch.object(netifaces, 'ifaddresses')
    def test_get_facts(self, mock_ifaddr, mock_eth, mock_hostname, mock_ip):
        mock_client = mock.Mock()
        mock_client.ip = mock.sentinel.dom0_himn_ip
        mock_eth.return_value = 'eth3'
        mock_ifaddr.return_value = {2: [{'netmask': u'255.255.0.0',
                                         'addr': u'169.254.0.2'}]}
        mock_hostname.return_value = 'traya'
        fake_ipv4s = [
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
        mock_ip.return_value = fake_ipv4s

        ret_facts = xenapi_facts.get_xenapi_facts(mock_client)

        expect_facts = {"domu_himn_ip": "169.254.0.2",
                        "domu_himn_eth": "eth3",
                        "dom0_hostname": "traya",
                        "dom0_ipv4s": fake_ipv4s}
        self.assertEqual(ret_facts, expect_facts)
        mock_eth.assert_called_with(mock.sentinel.dom0_himn_ip)
