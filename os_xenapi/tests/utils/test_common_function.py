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

import logging
import mock
import os

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

    @mock.patch.object(logging, 'basicConfig')
    @mock.patch.object(os.path, 'exists')
    @mock.patch.object(os, 'mkdir')
    def test_setup_logging(self, mock_mkdir, mock_exists, fake_log_conf):
        expect_log_file = 'fake_folder/fake_file'
        mock_exists.return_value = True

        common_function.setup_logging('fake_file', 'fake_folder/',
                                      'fake_debug_level')

        fake_log_conf.assert_called_once_with(
            filename=expect_log_file, level='fake_debug_level',
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        mock_mkdir.assert_not_called()
        mock_exists.assert_called_once_with('fake_folder/')

    @mock.patch.object(logging, 'basicConfig')
    @mock.patch.object(os.path, 'exists')
    @mock.patch.object(os, 'mkdir')
    def test_setup_logging_create_path(self, mock_mkdir, mock_exists,
                                       fake_log_conf):
        expect_log_file = 'fake_folder/fake_file'
        mock_exists.return_value = False

        common_function.setup_logging('fake_file', 'fake_folder/',
                                      'fake_debug_level')

        fake_log_conf.assert_called_once_with(
            filename=expect_log_file, level='fake_debug_level',
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        mock_mkdir.assert_called_once_with('fake_folder/')
        mock_exists.assert_called_once_with('fake_folder/')
