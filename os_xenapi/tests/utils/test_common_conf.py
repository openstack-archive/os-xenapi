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
from os_xenapi.utils import common_conf


class XenapiConfOptTestCase(base.TestCase):
    def test_enable_linux_bridge(self):
        client = mock.Mock()
        expect_cmd = "if [ -f /etc/modprobe.d/blacklist-bridge.conf ]; then\n"\
                     "    mv -f /etc/modprobe.d/blacklist-bridge.conf" \
                     "        /etc/modprobe.d/blacklist-bridge.conf_bak\n" \
                     "fi"

        common_conf.enable_linux_bridge(client)
        client.ssh.assert_called_once_with(expect_cmd)
