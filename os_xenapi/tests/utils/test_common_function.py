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
