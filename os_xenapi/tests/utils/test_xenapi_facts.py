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

import json
import mock

from os_xenapi.tests import base
from os_xenapi.utils import himn
from os_xenapi.utils import xenapi_facts


class XenapiFactsTestCase(base.TestCase):
    def test_hostname(self):
        mock_client = mock.Mock()
        out = 'fake_hostname\r\n'
        err = ''
        mock_client.ssh.return_value = (out, err)

        hostname = xenapi_facts.get_hostname(mock_client)

        mock_client.ssh.assert_called_with('hostname')
        self.assertEqual(hostname, 'fake_hostname')

    @mock.patch.object(xenapi_facts, 'get_hostname')
    @mock.patch.object(himn, 'detect_himn')
    def test_get_facts(self, mock_himn, mock_hostname):
        xenapi_facts.sshclient.SSHClient = mock.Mock
        mock_himn.return_value = ('eth3', [{'addr': u'169.254.0.2'}])
        mock_hostname.return_value = 'traya'

        facts_json = xenapi_facts.get_facts('169.254.0.1', 'root', 'passwd')

        expect_facts = {"local_himn_ip": "169.254.0.2",
                        "local_himn_eth": "eth3",
                        "hostname": "traya"}
        self.assertEqual(json.loads(facts_json), expect_facts)
