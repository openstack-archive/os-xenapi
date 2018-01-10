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

from os_xenapi.cmd import bootstrap
from os_xenapi.tests import base


class GetXenapiFactsTestCase(base.TestCase):
    def test_parse_args(self):
        argv = ['bootstrap', '-i', '169.254.0.1', '-u', 'root', '-p', 'passwd']

        return_opts = bootstrap._parse_args(argv)

        expect_opts = {'himn-ip': '169.254.0.1',
                       'passwd': 'passwd',
                       'user-name': 'root'}
        self.assertEqual(expect_opts, return_opts)

    def test_parse_args_with_filepath(self):
        argv = ['bootstrap', '-i', '169.254.0.1', '-u', 'root', '-p', 'passwd',
                '-f', '/path/to/file']

        return_opts = bootstrap._parse_args(argv)

        expect_opts = {'himn-ip': '169.254.0.1',
                       'passwd': 'passwd',
                       'user-name': 'root',
                       'xenapi-facts-file': '/path/to/file'}
        self.assertEqual(expect_opts, return_opts)

    @mock.patch.object(bootstrap, 'exit_with_usage')
    def test_parse_args_no_valid_option(self, mock_usage):
        # Verify if it will exit with prompting usage if no
        # valid options passed except the command name.
        argv = ['bootstrap']

        bootstrap._parse_args(argv)

        mock_usage.assert_called_with()

    @mock.patch.object(bootstrap, 'exit_with_usage')
    def test_parse_args_invalid_opts(self, mock_usage):
        # Verify if it will exit with prompting usage if pass in
        # wrong opts.
        argv = ['bootstrap', '-v', 'invalid_opt']

        bootstrap._parse_args(argv)

        mock_usage.assert_called_with()

    @mock.patch.object(bootstrap, 'exit_with_usage')
    def test_parse_args_lack_opts(self, mock_usage):
        # Verify if it will exit with prompting usage if not
        # pass in all required opts.
        argv = ['bootstrap', '-i', '169.254.0.1']

        bootstrap._parse_args(argv)

        mock_usage.assert_called_with()

    @mock.patch.object(bootstrap, '_parse_args')
    @mock.patch.object(bootstrap, 'SSHClient')
    @mock.patch.object(bootstrap, 'config_himn')
    @mock.patch.object(bootstrap, 'config_iptables')
    @mock.patch.object(bootstrap, 'install_plugins_to_dom0')
    @mock.patch.object(bootstrap, 'get_and_store_facts')
    @mock.patch.object(bootstrap, 'enable_linux_bridge')
    @mock.patch.object(bootstrap, 'setup_logging')
    def test_bootstrap(self, mock_setup_logging, mock_enable_lbr, mock_facts,
                       mock_plugin, mock_iptables, mock_himn, mock_client,
                       mock_parse):
        fake_opts = {'himn-ip': '169.254.0.1',
                     'passwd': 'passwd',
                     'user-name': 'root'}
        mock_parse.return_value = fake_opts
        mock_client.return_value = mock.sentinel.sshclient

        bootstrap.main()

        mock_client.assert_called_with('169.254.0.1', 'root', 'passwd')
        mock_himn.assert_called_with('169.254.0.1')
        mock_iptables.assert_called_with(mock.sentinel.sshclient)
        mock_plugin.assert_called_with(mock.sentinel.sshclient)
        mock_facts.assert_called_with(mock.sentinel.sshclient,
                                      bootstrap.DEF_XENAPI_FACTS_FILE)
        mock_enable_lbr.assert_called_with(mock.sentinel.sshclient)
        mock_setup_logging.assert_called_once_with(log_level=logging.DEBUG)
