# Copyright (c) 2017 Citrix Systems, Inc
# All Rights Reserved.
#
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

from os_xenapi.tests.plugins import plugin_test


class FakeXenAPIException(Exception):
    pass


class FakePluginErrorException(Exception):
    def __init__(self, details):
        self.err = details


class FakeSubprocessException(Exception):
    def __init__(self, details):
        self.err = details


class XenHostRunCmdTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(XenHostRunCmdTestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")

    def test_run_command(self):
        self.mock_patch_object(self.host.utils,
                               'run_command',
                               'fake_wrong_cmd_return')
        self.host._run_command('fake_command')

        self.host.utils.run_command.assert_called_once()

    def test_run_command_exception(self):
        side_effect = ([FakeSubprocessException('Subprocess exception')])
        self.mock_patch_object(self.host.utils,
                               'run_command',
                               'fake_wrong_cmd_return')
        self.host.utils.run_command.side_effect = side_effect
        self.host.utils.SubprocessException = FakeSubprocessException

        self.assertRaises(self.pluginlib.PluginError,
                          self.host._run_command,
                          'fake_command')
        self.host.utils.run_command.assert_called_once()
