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
import XenAPI


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
        self.host._run_command.return_value = ['', 'any_value']
        expected = [call(['xe', 'host-enable', 'uuid=fake_host_uuid']),
                    call(['xe', 'host-param-get', 'uuid=fake_host_uuid',
                         'param-name=enabled'])]
        self.host._run_command.side_effect = side_effects
        expected_status = {"status": 'disabled'}
        result_status = self.host.set_host_enabled(self.host, temp_dict)
        self.assertEqual(self.host._run_command.call_args_list, expected)
        self.assertEqual(json.loads(result_status), expected_status)

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
        expected_status = {"status": 'disabled'}
        result_status = self.host.set_host_enabled(self.host, temp_dict)
        self.assertEqual(self.host._run_command.call_args_list, expected)
        self.assertEqual(json.loads(result_status), expected_status)

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
