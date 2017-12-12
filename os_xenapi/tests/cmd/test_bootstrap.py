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

from os_xenapi.cmd import bootstrap
from os_xenapi.tests import base


class GetXenapiFactsTestCase(base.TestCase):
    @mock.patch.object(bootstrap, 'config_himn')
    @mock.patch.object(bootstrap, 'install_plugins_to_dom0')
    def test_get_xenapi_facts(self, mock_plugin, mock_himn):
        bootstrap.SSHClient = mock.Mock
        argv = ['-i', '169.254.0.1', '-u', 'root', '-p', 'passwd']

        bootstrap.main(argv)

        mock_himn.assert_called_with('169.254.0.1')
        mock_plugin.assert_called()

    @mock.patch.object(bootstrap, 'exit_with_usage')
    @mock.patch.object(bootstrap, 'config_himn')
    @mock.patch.object(bootstrap, 'install_plugins_to_dom0')
    def test_get_xenapi_facts_wrong_opt(self, mock_plugin, mock_himn,
                                        mock_usage):
        # Verify if it will exit with prompting usage if pass in
        # wrong opts.
        argv = ['-i', '169.254.0.1', '-u', 'root', '-v', 'invalid_opt']

        bootstrap.main(argv)

        mock_usage.assert_called_with()
        mock_himn.assert_not_called()
        mock_plugin.assert_not_called()

    @mock.patch.object(bootstrap, 'exit_with_usage')
    @mock.patch.object(bootstrap, 'config_himn')
    @mock.patch.object(bootstrap, 'install_plugins_to_dom0')
    def test_get_xenapi_facts_lack_opts(self, mock_plugin, mock_himn,
                                        mock_usage):
        # Verify if it will exit with prompting usage if pass in
        # wrong opts.
        argv = ['-i', '169.254.0.1']

        bootstrap.main(argv)

        mock_usage.assert_called_with()
        mock_himn.assert_not_called()
        mock_plugin.assert_not_called()
