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
import time


class FakeXenAPIException(Exception):
    pass


class XenHostRunCmdTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(XenHostRunCmdTestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")

    def test_run_command(self):
        self.mock_patch_object(self.host.utils,
                               'run_command',
                               'fake_run_cmd_return')
        cmd_result = self.host._run_command('fake_command')

        self.assertEqual(cmd_result, 'fake_run_cmd_return')
        self.host.utils.run_command.assert_called_with(
            'fake_command', cmd_input=None)

    def test_run_command_exception(self):
        side_effect = [self.host.utils.SubprocessException(
                       'fake_cmdline', 0,
                       'fake_out', 'fake_err')]
        self.mock_patch_object(self.host.utils,
                               'run_command',
                               'fake_run_cmd_return')
        self.host.utils.run_command.side_effect = side_effect

        self.assertRaises(self.pluginlib.PluginError,
                          self.host._run_command,
                          'fake_command')
        self.host.utils.run_command.assert_called_with(
            'fake_command', cmd_input=None)


class VMOperationTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(VMOperationTestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")
        self.mock_patch_object(self.host,
                               '_run_command',
                               'fake_run_cmd_return')

    @mock.patch.object(time, 'sleep')
    def test_resume_compute(self, mock_sleep):
        self.mock_patch_object(self.session.xenapi.VM,
                               'start')
        self.host._resume_compute(self.session,
                                  'fake_compute_ref',
                                  'fake_compute_uuid')

        self.session.xenapi.VM.start.assert_called_with(
            'fake_compute_ref', False, True)
        mock_sleep.time.assert_not_called()

    @mock.patch.object(time, 'sleep')
    def test_resume_compute_exception_compute_VM_restart(self, mock_sleep):
        side_effect_xenapi_failure = FakeXenAPIException
        self.mock_patch_object(self.session.xenapi.VM,
                               'start')
        self.host.XenAPI.Failure = FakeXenAPIException
        self.session.xenapi.VM.start.side_effect = \
            side_effect_xenapi_failure

        self.host._resume_compute(self.session,
                                  'fake_compute_ref',
                                  'fake_compute_uuid')
        self.session.xenapi.VM.start.assert_called_with(
            'fake_compute_ref', False, True)
        self.host._run_command.assert_called_with(
            ["xe", "vm-start", "uuid=%s" % 'fake_compute_uuid']
        )
        mock_sleep.assert_not_called()

    @mock.patch.object(time, 'sleep')
    def test_resume_compute_exception_wait_slave_available(self, mock_sleep):
        side_effect_xenapi_failure = FakeXenAPIException
        side_effect_plugin_error = [self.pluginlib.PluginError(
                                    "Wait for the slave to become available"),
                                    None]
        self.mock_patch_object(self.session.xenapi.VM,
                               'start')
        self.session.xenapi.VM.start.side_effect = \
            side_effect_xenapi_failure
        self.host._run_command.side_effect = side_effect_plugin_error
        self.host.XenAPI.Failure = FakeXenAPIException
        expected = [call(["xe", "vm-start", "uuid=%s" % 'fake_compute_uuid']),
                    call(["xe", "vm-start", "uuid=%s" % 'fake_compute_uuid'])]

        self.host._resume_compute(self.session,
                                  'fake_compute_ref',
                                  'fake_compute_uuid')
        self.session.xenapi.VM.start.assert_called_with(
            'fake_compute_ref', False, True)
        self.assertEqual(expected, self.host._run_command.call_args_list)
        mock_sleep.assert_called_once()

    @mock.patch.object(time, 'sleep')
    def test_resume_compute_exception_unrecoverable(self, mock_sleep):
        fake_compute_ref = -1
        side_effect_xenapi_failure = FakeXenAPIException
        side_effect_plugin_error = (
            [self.pluginlib.PluginError]
            * self.host.DEFAULT_TRIES)
        self.mock_patch_object(self.session.xenapi.VM,
                               'start')
        self.session.xenapi.VM.start.side_effect = \
            side_effect_xenapi_failure
        self.host.XenAPI.Failure = FakeXenAPIException
        self.host._run_command.side_effect = side_effect_plugin_error

        self.assertRaises(self.pluginlib.PluginError,
                          self.host._resume_compute,
                          self.session,
                          fake_compute_ref,
                          'fake_compute_uuid')
        self.session.xenapi.VM.start.assert_called_with(
            -1, False, True)
        self.host._run_command.assert_called_with(
            ["xe", "vm-start", "uuid=%s" % 'fake_compute_uuid']
        )
        mock_sleep.assert_called()

    def test_set_host_enabled_no_enabled_key_in_arg_dict(self):
        temp_dict = {}
        self.assertRaises(self.pluginlib.PluginError,
                          self.host.set_host_enabled,
                          self.host, temp_dict)

    def test_set_host_enabled_unexpected_enabled_key(self):
        temp_dict = {}
        temp_dict.update({'enabled': 'unexpected_status'})
        temp_dict.update({'host_uuid': 'fake_host_uuid'})
        self.assertRaises(self.pluginlib.PluginError,
                          self.host.set_host_enabled,
                          self.host, temp_dict)

    def test_set_host_enabled_host_enable_disable_cmd_return_not_empty(self):
        temp_dict = {}
        temp_dict.update({'enabled': 'true'})
        temp_dict.update({'host_uuid': 'fake_host_uuid'})
        fake_run_command_return = 'not empty'
        self.host._run_command.return_value = fake_run_command_return
        self.assertRaises(self.pluginlib.PluginError,
                          self.host.set_host_enabled,
                          self.host, temp_dict)
        self.host._run_command.assert_called_once

    def test_set_host_enabled_request_host_enabled(self):
        temp_dict = {}
        side_effects = ['', 'any_value']
        temp_dict.update({'enabled': 'true'})
        temp_dict.update({'host_uuid': 'fake_host_uuid'})
        expected = [call(['xe', 'host-enable', 'uuid=fake_host_uuid']),
                    call(['xe', 'host-param-get', 'uuid=fake_host_uuid',
                         'param-name=enabled'])]
        self.host._run_command.side_effect = side_effects
        self.host.set_host_enabled(self.host, temp_dict)
        self.assertEqual(self.host._run_command.call_args_list, expected)

    def test_set_host_enabled_request_cmd_host_disable(self):
        temp_dict = {}
        side_effects = ['', 'any_value']
        temp_dict.update({'enabled': 'false'})
        temp_dict.update({'host_uuid': 'fake_host_uuid'})
        expected = [call(["xe", "host-disable", "uuid=%s" %
                         temp_dict['host_uuid']],),
                    call(["xe", "host-param-get", "uuid=%s"
                         % temp_dict['host_uuid'],
                         "param-name=enabled"],)]
        self.host._run_command.side_effect = side_effects
        self.host.set_host_enabled(self.host, temp_dict)
        self.assertEqual(self.host._run_command.call_args_list, expected)

    def test_set_host_enabled_confirm_host_enabled(self):
        temp_dict = {}
        side_effects = ['', 'true']
        temp_dict.update({'enabled': 'true'})
        temp_dict.update({'host_uuid': 'fake_host_uuid'})
        self.host._run_command.side_effect = side_effects
        result_status = self.host.set_host_enabled(self.host, temp_dict)
        self.assertEqual(result_status, '{"status": "enabled"}')

    def test_set_host_enabled_confirm_host_disabled(self):
        temp_dict = {}
        side_effects = ['', 'any_value']
        temp_dict.update({'enabled': 'false'})
        temp_dict.update({'host_uuid': 'fake_host_uuid'})
        self.host._run_command.side_effect = side_effects
        result_status = self.host.set_host_enabled(self.host, temp_dict)
        self.assertEqual(result_status, '{"status": "disabled"}')


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
        self.host._get_config_dict.assert_called_once()

    def test_get_config_json(self):
        temp_dict = {'params': '{"key": "fake_key"}'}
        fake_conf_dict = {'fake_key': 'fake_conf_key'}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               fake_conf_dict)
        config_return = self.host.get_config(self.host, temp_dict)
        self.assertEqual(json.loads(config_return), 'fake_conf_key')
        self.host._get_config_dict.assert_called_once()

    def test_get_config_dict(self):
        temp_dict = {'params': {"key": "fake_key"}}
        fake_conf_dict = {'fake_key': 'fake_conf_key'}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               fake_conf_dict)
        config_return = self.host.get_config(self.host, temp_dict)
        self.assertEqual(json.loads(config_return), 'fake_conf_key')
        self.host._get_config_dict.assert_called_once()

    def test_set_config_remove_none_key(self):
        temp_arg_dict = {'params': {"key": "fake_key", "value": None}}
        temp_conf = {'fake_key': 'fake_value'}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               temp_conf)
        self.mock_patch_object(self.host,
                               '_write_config_dict')

        self.host.set_config(self.host, temp_arg_dict)
        self.assertTrue("fake_key" not in temp_conf)
        self.host._get_config_dict.assert_called_once()
        self.host._write_config_dict.assert_called_with(temp_conf)

    def test_set_config_overwrite_key_value(self):
        temp_arg_dict = {'params': {"key": "fake_key", "value": "new_value"}}
        temp_conf = {'fake_key': 'fake_value'}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               temp_conf)
        self.mock_patch_object(self.host,
                               '_write_config_dict')

        self.host.set_config(self.host, temp_arg_dict)
        self.assertTrue('fake_key' in temp_conf)
        self.host._get_config_dict.assert_called_once()
        temp_conf.update({'fake_key': 'new_value'})
        self.host._write_config_dict.assert_called_with(temp_conf)


class NetworkTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(NetworkTestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")
        self.mock_patch_object(self.host,
                               '_run_command',
                               'fake_run_cmd_return')

    def test_ovs_add_patch_port(self):
        brige_name = 'fake_brige_name'
        port_name = 'fake_port_name'
        peer_port_name = 'fake_peer_port_name'
        side_effects = [brige_name, port_name, peer_port_name]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists', 'del-port',
                             port_name, '--', 'add-port', brige_name,
                             'fake_port_name', '--', 'set', 'interface',
                             'fake_port_name', 'type=patch',
                             'options:peer=%s' % peer_port_name]
        expected_pluginlib_arg_list = [call('fake_args', 'bridge_name'),
                                       call('fake_args', 'port_name'),
                                       call('fake_args', 'peer_port_name')]

        self.host._ovs_add_patch_port('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_ovs_del_port(self):
        bridge_name = 'fake_brige_name'
        port_name = 'fake_port_name'
        side_effects = [bridge_name, port_name]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists', 'del-port',
                             bridge_name, port_name]
        expected_pluginlib_arg_list = [call('fake_args', 'bridge_name'),
                                       call('fake_args', 'port_name')]

        self.host._ovs_del_port('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_ovs_del_br(self):
        bridge_name = 'fake_brige_name'
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               bridge_name)
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists',
                             'del-br', bridge_name]

        self.host._ovs_del_br('fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'bridge_name')
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ovs_set_if_external_id(self):
        interface = 'fake_interface'
        extneral_id = 'fake_extneral_id'
        value = 'fake_value'
        side_effects = [interface, extneral_id, value]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', 'set', 'Interface', interface,
                             'external-ids:%s=%s' % (extneral_id, value)]
        expected_pluginlib_arg_list = [call('fake_args', 'interface'),
                                       call('fake_args', 'extneral_id'),
                                       call('fake_args', 'value')]

        self.host._ovs_set_if_external_id('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_ovs_add_port(self):
        bridge_name = 'fake_brige_name'
        port_name = 'fake_port_name'
        side_effects = [bridge_name, port_name]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists', 'del-port',
                             port_name, '--', 'add-port', bridge_name,
                             port_name]
        expected_pluginlib_arg_list = [call('fake_args', 'bridge_name'),
                                       call('fake_args', 'port_name')]

        self.host._ovs_add_port('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_ovs_create_port(self):
        bridge_name = 'fake_brige_name'
        port_name = 'fake_port_name'
        iface_id = 'fake_iface_id'
        mac = 'fake_mac'
        status = 'fake_status'
        side_effects = [bridge_name, port_name, iface_id, mac, status]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists', 'del-port',
                             port_name, '--', 'add-port', bridge_name,
                             port_name, '--', 'set', 'Interface', port_name,
                             'external_ids:iface-id=%s' % iface_id,
                             'external_ids:iface-status=%s' % status,
                             'external_ids:attached-mac=%s' % mac,
                             'external_ids:xs-vif-uuid=%s' % iface_id]
        expected_pluginlib_arg_list = [call('fake_args', 'bridge'),
                                       call('fake_args', 'port'),
                                       call('fake_args', 'iface-id'),
                                       call('fake_args', 'mac'),
                                       call('fake_args', 'status')]

        self.host._ovs_create_port('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_ip_link_get_dev(self):
        device_name = 'fake_device_name'
        expected_cmd_args = ['ip', 'link', 'show', device_name]
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               device_name)

        self.host._ip_link_get_dev('fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'device_name')
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ip_link_del_dev(self):
        device_name = 'fake_device_name'
        expected_cmd_args = ['ip', 'link', 'delete', device_name]
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               'fake_device_name')

        self.host._ip_link_del_dev('fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'device_name')
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ip_link_add_veth_pair(self):
        dev1_name = 'fake_brige_name'
        dev2_name = 'fake_port_name'
        side_effects = [dev1_name, dev2_name]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ip', 'link', 'add', dev1_name, 'type',
                             'veth', 'peer', 'name', dev2_name]
        expected_pluginlib_arg_list = [call('fake_args', 'dev1_name'),
                                       call('fake_args', 'dev2_name')]

        self.host._ip_link_add_veth_pair('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_ip_link_set_dev(self):
        device_name = 'fake_device_name'
        option = 'fake_option'
        side_effects = [device_name, option]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ip', 'link', 'set', device_name, option]
        expected_pluginlib_arg_list = [call('fake_args', 'device_name'),
                                       call('fake_args', 'option')]

        self.host._ip_link_set_dev('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_ip_link_set_promisc(self):
        device_name = 'fake_device_name'
        option = 'fake_option'
        side_effects = [device_name, option]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ip', 'link', 'set', device_name, 'promisc',
                             option]
        expected_pluginlib_arg_list = [call('fake_args', 'device_name'),
                                       call('fake_args', 'option')]

        self.host._ip_link_set_promisc('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_brctl_add_br(self):
        bridge_name = 'fake_bridge_name'
        cmd_args = 'fake_option'
        side_effects = [bridge_name, cmd_args]
        self.pluginlib.exists.side_effect = side_effects
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               bridge_name)
        expected_cmd_args = ['brctl', 'addbr', bridge_name]

        self.host._brctl_add_br('fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'bridge_name')
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_brctl_del_br(self):
        bridge_name = 'fake_bridge_name'
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               bridge_name)
        expected_cmd_args = ['brctl', 'delbr', bridge_name]

        self.host._brctl_del_br('fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'bridge_name')
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_brctl_set_fd(self):
        bridge_name = 'fake_device_name'
        fd = 'fake_fd'
        side_effects = [bridge_name, fd]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['brctl', 'setfd', bridge_name, fd]
        expected_pluginlib_arg_list = [call('fake_args', 'bridge_name'),
                                       call('fake_args', 'fd')]

        self.host._brctl_set_fd('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_brctl_set_stp(self):
        bridge_name = 'fake_device_name'
        option = 'fake_option'
        side_effects = [bridge_name, option]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['brctl', 'stp', bridge_name, option]
        expected_pluginlib_arg_list = [call('fake_args', 'bridge_name'),
                                       call('fake_args', 'option')]

        self.host._brctl_set_stp('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_brctl_add_if(self):
        bridge_name = 'fake_device_name'
        if_name = 'fake_if_name'
        side_effects = [bridge_name, if_name]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['brctl', 'addif', bridge_name, if_name]
        expected_pluginlib_arg_list = [call('fake_args', 'bridge_name'),
                                       call('fake_args', 'interface_name')]

        self.host._brctl_add_if('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

    def test_brctl_del_if(self):
        bridge_name = 'fake_device_name'
        if_name = 'fake_if_name'
        side_effects = [bridge_name, if_name]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['brctl', 'delif', bridge_name, if_name]
        expected_pluginlib_arg_list = [call('fake_args', 'bridge_name'),
                                       call('fake_args', 'interface_name')]

        self.host._brctl_del_if('fake_args')
        self.host._run_command.assert_called_with(expected_cmd_args)
        self.assertEqual(self.pluginlib.exists.call_args_list,
                         expected_pluginlib_arg_list)

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

    def test_network_config_invalid_cmd(self):
        fake_invalid_cmd = 0
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               fake_invalid_cmd)

        self.assertRaises(self.pluginlib.PluginError,
                          self.host.network_config,
                          'fake_session', 'fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'cmd')

    def test_network_config_unexpected_cmd(self):
        fake_unexpected_cmd = 'fake_unknow_cmd'
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               fake_unexpected_cmd)

        self.assertRaises(self.pluginlib.PluginError,
                          self.host.network_config,
                          'fake_session', 'fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'cmd')

    def test_network_config(self):
        fake_valid_cmd = 'ovs_add_patch_port'
        side_effects = [fake_valid_cmd, 'fake_cmd_args']
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        mock_func = self.mock_patch_object(self.host,
                                           '_ovs_add_patch_port')
        self.host.ALLOWED_NETWORK_CMDS['ovs_add_patch_port'] = mock_func

        self.host.network_config('fake_session', 'fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'args')
        self.host._ovs_add_patch_port.assert_called_with('fake_cmd_args')


class XenHostTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(XenHostTestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")
        self.mock_patch_object(self.host,
                               '_run_command',
                               'fake_run_cmd_return')

    def test_clean_up(self):
        fake_arg_dict = {
            'enabled': 'enabled',
            'memory-total': '0',
            'memory-overhead': '1',
            'memory-free': '2',
            'memory-free-computed': '3',
            'uuid': 'fake_uuid',
            'name-label': 'fake_name-label',
            'name-description': 'fake_name-description',
            'hostname': 'fake_hostname',
            'address': 'fake_address',
            'other-config': 'config:fake_other-config_1; \
             config:fake_other-config_2',
            'capabilities': 'fake_cap_1; fake_cap_2',
            'cpu_info': 'cpu_count:1; family:101; unknow:1'
        }
        expected_out = {
            'enabled': 'enabled',
            'host_memory': {'total': 0,
                            'overhead': 1,
                            'free': 2,
                            'free-computed': 3},
            'host_uuid': 'fake_uuid',
            'host_name-label': 'fake_name-label',
            'host_name-description': 'fake_name-description',
            'host_hostname': 'fake_hostname',
            'host_ip_address': 'fake_address',
            'host_other-config': {'config': 'fake_other-config_1',
                                  'config': 'fake_other-config_2'},
            'host_capabilities': ['fake_cap_1', 'fake_cap_2'],
            'host_cpu_info': {'cpu_count': 1, 'family': 101,
                              'unknow': '1'}
        }

        out = self.host.cleanup(fake_arg_dict)
        self.assertEqual(out, expected_out)

    def test_clean_up_exception_invalid_memory_value(self):
        fake_arg_dict = {
            'enabled': 'enabled',
            'memory-total': 'invalid',
            'memory-overhead': 'invalid',
            'memory-free': 'invalid',
            'memory-free-computed': 'invalid',
            'uuid': 'fake_uuid',
            'name-label': 'fake_name-label',
            'name-description': 'fake_name-description',
            'hostname': 'fake_hostname',
            'address': 'fake_address',
            'other-config': 'config:fake_other-config_1; \
             config:fake_other-config_2',
            'capabilities': 'fake_cap_1; fake_cap_2',
            'cpu_info': 'cpu_count:1; family:101; unknow:1'
        }
        expected_out = {
            'enabled': 'enabled',
            'host_memory': {'total': None,
                            'overhead': None,
                            'free': None,
                            'free-computed': None},
            'host_uuid': 'fake_uuid',
            'host_name-label': 'fake_name-label',
            'host_name-description': 'fake_name-description',
            'host_hostname': 'fake_hostname',
            'host_ip_address': 'fake_address',
            'host_other-config': {'config': 'fake_other-config_1',
                                  'config': 'fake_other-config_2'},
            'host_capabilities': ['fake_cap_1', 'fake_cap_2'],
            'host_cpu_info': {'cpu_count': 1, 'family': 101,
                              'unknow': '1'}
        }

        out = self.host.cleanup(fake_arg_dict)
        self.assertEqual(out, expected_out)

    def test_query_gc_running(self):
        fake_cmd_result = "Currently running: True"
        self.host._run_command.return_value = fake_cmd_result
        query_gc_result = self.host.query_gc('fake_session',
                                             'fake_sr_uuid',
                                             'fake_vdi_uuid')
        self.assertTrue(query_gc_result)
        self.host._run_command.assert_called_with(
            ["/opt/xensource/sm/cleanup.py",
             "-q", "-u", 'fake_sr_uuid'])

    def test_query_gc_not_running(self):
        fake_cmd_result = "Currently running: False"
        self.host._run_command.return_value = fake_cmd_result
        query_gc_result = self.host.query_gc('fake_session',
                                             'fake_sr_uuid',
                                             'fake_vdi_uuid')
        self.assertFalse(query_gc_result)
        self.host._run_command.assert_called_with(
            ["/opt/xensource/sm/cleanup.py",
             "-q", "-u", 'fake_sr_uuid'])

    def test_get_pci_device_details(self):
        self.host.get_pci_device_details('fake_session')
        self.host._run_command.assert_called_with(
            ["lspci", "-vmmnk"])

    def test_get_pci_type_no_domain(self):
        fake_pci_device = '00:00.0'
        self.host._run_command.return_value = ['fake_pci_type', ]

        self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + '0000:'
             + fake_pci_device + "/"])

    def test_get_pci_type_physfn(self):
        fake_pci_device = '0000:00:00.0'
        self.host._run_command.return_value = ['physfn', ]

        output = self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + fake_pci_device + "/"])
        self.assertEqual(output, 'type-VF')

    def test_get_pci_type_virtfn(self):
        fake_pci_device = '0000:00:00.0'
        self.host._run_command.return_value = ['virtfn', ]

        output = self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + fake_pci_device + "/"])
        self.assertEqual(output, 'type-PF')

    def test_get_pci_type_PCI(self):
        fake_pci_device = '0000:00:00.0'
        self.host._run_command.return_value = ['other', ]

        output = self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + fake_pci_device + "/"])
        self.assertEqual(output, 'type-PCI')
