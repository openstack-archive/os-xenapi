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

from os_xenapi.cmd import get_xenapi_facts
from os_xenapi.tests import base
from os_xenapi.utils import xenapi_facts


class GetXenapiFactsTestCase(base.TestCase):
    @mock.patch.object(xenapi_facts, 'get_facts')
    def test_get_xenapi_facts(self, mock_get):
        argv = ['-i', '169.254.0.1', '-u', 'root', '-p', 'passwd']

        get_xenapi_facts.main(argv)

        mock_get.assert_called_with('169.254.0.1', 'root', 'passwd')

    @mock.patch.object(get_xenapi_facts, 'exit_with_usage')
    @mock.patch.object(xenapi_facts, 'get_facts')
    def test_get_xenapi_facts_wrong_opt(self, mock_get, mock_usage):
        # Verify if it will exit with prompting usage if pass in
        # wrong opts.
        argv = ['-i', '169.254.0.1', '-u', 'root', '-v', 'invalid_opt']

        get_xenapi_facts.main(argv)

        mock_usage.assert_called_with()
        mock_get.assert_not_called()

    @mock.patch.object(get_xenapi_facts, 'exit_with_usage')
    @mock.patch.object(xenapi_facts, 'get_facts')
    def test_get_xenapi_facts_lack_opts(self, mock_get, mock_usage):
        # Verify if it will exit with prompting usage if not giving
        # all required opts.
        argv = ['-i', '169.254.0.1']

        get_xenapi_facts.main(argv)

        mock_usage.assert_called_with()
        mock_get.assert_not_called()
