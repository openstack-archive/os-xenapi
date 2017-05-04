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
from mock import call
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


class HostOptTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(HostOptTestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")
        self.mock_patch_object(self.host,
                               '_run_command',
                               'fake_run_cmd_return')

    # may be removed because the operation would be deprecate
    def test_power_action_disable_cmd_result_not_empty(self):
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        self.host._run_command.return_value = 'not_empty'
        expected_cmd_arg = ["xe", "host-disable", "uuid=%s" %
                            'fake_host_uuid']

        self.assertRaises(self.pluginlib.PluginError,
                          self.host._power_action,
                          'fake_action', temp_arg_dict)
        self.host._run_command.assert_called_with(expected_cmd_arg)

    # may be removed because the operation would be deprecate
    def test_power_action_shutdown_cmd_result_not_empty(self):
        side_effects = [None, 'not_empty']
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        self.host._run_command.side_effect = side_effects
        expected_cmd_arg_list = [call(["xe", "host-disable", "uuid=%s"
                                      % 'fake_host_uuid']),
                                 call(["xe", "vm-shutdown", "--multiple",
                                      "resident-on=%s" % 'fake_host_uuid'])]

        self.assertRaises(self.pluginlib.PluginError,
                          self.host._power_action,
                          'fake_action', temp_arg_dict)
        self.assertEqual(self.host._run_command.call_args_list,
                         expected_cmd_arg_list)

    # may be removed because the operation would be deprecate
    def test_power_action_input_cmd_result_not_empty(self):
        side_effects = [None, None, 'not_empty']
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        self.host._run_command.side_effect = side_effects
        cmds = {"reboot": "host-reboot",
                "startup": "host-power-on",
                "shutdown": "host-shutdown"}
        fake_action = 'reboot'  # 'statup' and 'shutdown' should be same
        expected_cmd_arg_list = [call(["xe", "host-disable", "uuid=%s"
                                      % 'fake_host_uuid']),
                                 call(["xe", "vm-shutdown", "--multiple",
                                      "resident-on=%s" % 'fake_host_uuid']),
                                 call(["xe", cmds[fake_action], "uuid=%s" %
                                      'fake_host_uuid'])]

        self.assertRaises(self.pluginlib.PluginError,
                          self.host._power_action,
                          fake_action, temp_arg_dict)
        self.assertEqual(self.host._run_command.call_args_list,
                         expected_cmd_arg_list)

    def test_power_action(self):
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        self.host._run_command.return_value = None
        cmds = {"reboot": "host-reboot",
                "startup": "host-power-on",
                "shutdown": "host-shutdown"}
        fake_action = 'reboot'  # 'statup' and 'shutdown' should be same
        expected_cmd_arg_list = [call(["xe", "host-disable", "uuid=%s"
                                      % 'fake_host_uuid']),
                                 call(["xe", "vm-shutdown", "--multiple",
                                      "resident-on=%s" % 'fake_host_uuid']),
                                 call(["xe", cmds[fake_action], "uuid=%s" %
                                      'fake_host_uuid'])]
        expected_result = {"power_action": fake_action}

        action_result = self.host._power_action(fake_action, temp_arg_dict)
        self.assertEqual(self.host._run_command.call_args_list,
                         expected_cmd_arg_list)
        self.assertEqual(action_result, expected_result)

    def test_host_reboot(self):
        fake_action = 'reboot'
        self.mock_patch_object(self.host,
                               '_power_action',
                               'fake_action_result')
        self.host.host_reboot(self.host, 'fake_arg_dict')

        self.host._power_action.assert_called_with(fake_action,
                                                   'fake_arg_dict')

    def test_host_shutdown(self):
        fake_action = 'shutdown'
        self.mock_patch_object(self.host,
                               '_power_action',
                               'fake_action_result')
        self.host.host_shutdown(self.host, 'fake_arg_dict')

        self.host._power_action.assert_called_with(fake_action,
                                                   'fake_arg_dict')

    def test_host_start(self):
        fake_action = 'startup'
        self.mock_patch_object(self.host,
                               '_power_action',
                               'fake_action_result')
        self.host.host_start(self.host, 'fake_arg_dict')

        self.host._power_action.assert_called_with(fake_action,
                                                   'fake_arg_dict')

    def test_host_join(self):
        temp_arg_dict = {'url': 'fake_url',
                         'user': 'fake_user',
                         'password': 'fake_password',
                         'master_addr': 'fake_master_addr',
                         'master_user': 'fake_master_user',
                         'master_pass': 'fake_master_pass',
                         'compute_uuid': 'fake_compute_uuid'}
        self.mock_patch_object(self.host, '_resume_compute')
        self.host.XenAPI = mock.Mock()
        self.host.XenAPI.Session = mock.Mock()

        self.host.host_join(self.host, temp_arg_dict)
        self.host.XenAPI.Session().login_with_password.assert_called_once()
        self.host.XenAPI.Session().xenapi.pool.join.assert_called_with(
            'fake_master_addr',
            'fake_master_user',
            'fake_master_pass')
        self.host._resume_compute.assert_called_with(
            self.host.XenAPI.Session(),
            self.host.XenAPI.Session().xenapi.VM.get_by_uuid(
                'fake_compute_uuid'),
            'fake_compute_uuid')

    def test_host_join_force_join(self):
        temp_arg_dict = {'force': 'true',
                         'master_addr': 'fake_master_addr',
                         'master_user': 'fake_master_user',
                         'master_pass': 'fake_master_pass',
                         'compute_uuid': 'fake_compute_uuid'}
        self.mock_patch_object(self.host, '_resume_compute')
        self.host.XenAPI = mock.Mock()
        self.host.XenAPI.Session = mock.Mock()

        self.host.host_join(self.host, temp_arg_dict)
        self.host.XenAPI.Session().login_with_password.assert_called_once()
        self.host.XenAPI.Session().xenapi.pool.join_force.assert_called_with(
            'fake_master_addr',
            'fake_master_user',
            'fake_master_pass')
        self.host._resume_compute.assert_called_with(
            self.host.XenAPI.Session(),
            self.host.XenAPI.Session().xenapi.VM.get_by_uuid(
                'fake_compute_uuid'),
            'fake_compute_uuid')

    def test_host_data(self):
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        fake_dict_after_cleanup = {'new_key': 'new_value'}
        fake_config_setting = {'config': 'fake_config_setting'}
        self.host._run_command.return_value = 'fake_resp'
        self.mock_patch_object(self.host,
                               'parse_response',
                               'fake_parsed_data')
        self.mock_patch_object(self.host,
                               'cleanup',
                               fake_dict_after_cleanup)
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               fake_config_setting)
        expected_ret_dict = fake_dict_after_cleanup
        expected_ret_dict.update(fake_config_setting)

        return_host_data = self.host.host_data(self.host,
                                               temp_arg_dict)
        self.host._run_command.assert_called_with(
            ["xe", "host-param-list", "uuid=%s" % temp_arg_dict['host_uuid']]
        )
        self.host.parse_response.assert_called_with('fake_resp')
        self.host.cleanup('fake_parsed_data')
        self.host._get_config_dict.assert_called_once()
        self.assertEqual(expected_ret_dict, json.loads(return_host_data))

    def test_parse_response(self):
        fake_resp = 'fake_name ( fake_flag): fake_value'
        expected_parsed_resp = {'fake_name': 'fake_value'}
        result_data = self.host.parse_response(fake_resp)
        self.assertEqual(result_data, expected_parsed_resp)

    def test_parse_response_one_invalid_line(self):
        fake_resp = "(exeception line)\n \
                     fake_name ( fake_flag): fake_value"
        expected_parsed_resp = {'fake_name': 'fake_value'}

        result_data = self.host.parse_response(fake_resp)
        self.assertEqual(result_data, expected_parsed_resp)

    def test_host_uptime(self):
        self.host._run_command.return_value = 'fake_uptime'
        uptime_return = self.host.host_uptime(self.host, 'fake_arg_dict')

        self.assertEqual(uptime_return, '{"uptime": "fake_uptime"}')
