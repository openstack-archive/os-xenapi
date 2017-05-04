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

try:
    import json
except ImportError:
    import simplejson as json
import mock
from os_xenapi.tests.plugins import plugin_test


class XenHostRunCmdTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(XenHostRunCmdTestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")

    def test_run_command(self):
        self.mock_patch_object(self.host.utils,
                               'run_command',
                               'fake_wrong_cmd_return')
        cmd_result = self.host._run_command('fake_command')

        self.assertEqual(cmd_result, 'fake_wrong_cmd_return')
        self.host.utils.run_command.assert_called_with(
            'fake_command', cmd_input=None)

    def test_run_command_exception(self):
        side_effect = [self.host.utils.SubprocessException(
                       'fake_cmdline', 0,
                       'fake_out', 'fake_err')]
        self.mock_patch_object(self.host.utils,
                               'run_command',
                               'fake_wrong_cmd_return')
        self.host.utils.run_command.side_effect = side_effect

        self.assertRaises(self.pluginlib.PluginError,
                          self.host._run_command,
                          'fake_command')
        self.host.utils.run_command.assert_called_with(
            'fake_command', cmd_input=None)


class ConfigOptTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(ConfigOptTestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")
        self.mock_patch_object(self.host,
                               '_run_command',
                               'fake_run_cmd_return')

    def test_get_config_no_config_key(self):
        temp_dict = {'params': '{"key": "fake_key"}'}
        fake_conf_dict = {}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               fake_conf_dict)

        config_return = self.host.get_config(self.host, temp_dict)
        self.assertEqual(json.loads(config_return), "None")
        self.host._get_config_dict.assert_called_once

    def test_get_config_config_key_not_none(self):
        temp_dict = {'params': '{"key": "fake_key"}'}
        fake_conf_dict = {'fake_key': 'fake_conf_key'}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               fake_conf_dict)
        config_return = self.host.get_config(self.host, temp_dict)
        self.assertEqual(json.loads(config_return), 'fake_conf_key')
        self.host._get_config_dict.assert_called_once

    def test_get_config_json_load_exception(self):
        temp_dict = {'params': {"key": "fake_key"}}
        fake_conf_dict = {'fake_key': 'fake_conf_key'}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               fake_conf_dict)
        config_return = self.host.get_config(self.host, temp_dict)
        self.assertEqual(json.loads(config_return), 'fake_conf_key')
        self.host._get_config_dict.assert_called_once

    @mock.patch.object(json, 'loads')
    def test_set_config_remove_none_key(self, mock_json_loads):
        temp_arg_dict = {'params': 'fake_params'}
        temp_dict = {'key': 'fake_key', 'value': None}
        mock_json_loads.return_value = temp_dict
        temp_conf = {temp_dict['key']: 'fake_key'}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               temp_conf)
        self.mock_patch_object(self.host,
                               '_write_config_dict')

        self.host.set_config(self.host, temp_arg_dict)
        self.assertTrue("fake_key" not in temp_conf)
        self.host._get_config_dict.assert_called_once()
        temp_conf.pop('key', None)
        self.host._write_config_dict.assert_called_with(temp_conf)

    @mock.patch.object(json, 'loads')
    def test_set_config_overwrite_key_value(self, mock_json_loads):
        temp_arg_dict = {'params': 'fake_params'}
        temp_dict = {'key': 'fake_key', 'value': 'not_none'}
        mock_json_loads.return_value = temp_dict
        temp_conf = {temp_dict['key']: 'fake_key'}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               temp_conf)
        self.mock_patch_object(self.host,
                               '_write_config_dict')

        self.host.set_config(self.host, temp_arg_dict)
        self.assertTrue('fake_key' in temp_conf)
        self.host._get_config_dict.assert_called_once()
        temp_conf.update({temp_dict['key']: temp_dict['value']})
        self.host._write_config_dict.assert_called_with(temp_conf)

    @mock.patch.object(json, 'loads')
    def test_iptables_config(self, mock_json_loads):
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               'fake_cmd_args')
        self.mock_patch_object(self.pluginlib,
                               'optional',
                               'fake_cmd_pro_input')
        self.host._run_command.return_value = 'fake_run_cmd_resule'
        mock_json_loads.return_value = ['iptables-save']
        expected = json.dumps(dict(out='fake_run_cmd_resule', err=''))

        ret_str = self.host.iptables_config('fake_session', 'fake_args')
        self.pluginlib.exists.assert_called_once()
        self.pluginlib.optional.assert_called_once()
        mock_json_loads.assert_called_with('fake_cmd_args')
        self.assertEqual(ret_str, expected)
        self.host._run_command.assert_called_with(
            map(str, ['iptables-save']), 'fake_cmd_pro_input')

    @mock.patch.object(json, 'loads')
    def test_iptables_config_plugin_error(self, mock_json_loads):
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.mock_patch_object(self.pluginlib,
                               'optional')

        self.assertRaises(self.pluginlib.PluginError,
                          self.host.iptables_config,
                          'fake_session', 'fake_args')
        self.pluginlib.exists.assert_called_once()
        self.pluginlib.optional.assert_called_once()
        mock_json_loads.assert_called_with(None)
