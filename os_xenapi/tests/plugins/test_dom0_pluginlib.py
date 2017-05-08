# Copyright (c) 2016 Citrix Systems
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

import mock
import os
from os_xenapi.tests.plugins import plugin_test
import time


class FakeUnplugException(Exception):
    def __init__(self, details):
        self.details = details


class PluginlibDom0(plugin_test.PluginTestBase):
    def setUp(self):
        super(PluginlibDom0, self).setUp()
        self.dom0_pluginlib = self.load_plugin("dom0_pluginlib.py")

    @mock.patch.object(os.path, 'exists')
    def test_configure_logging_log_dir_not_exist(self, mock_path_exist):
        name = 'fake_name'
        mock_Logger_setLevel = self.mock_patch_object(
            self.dom0_pluginlib.logging.Logger, 'setLevel')
        mock_sysh_setLevel = self.mock_patch_object(
            self.dom0_pluginlib.logging.handlers.SysLogHandler, 'setLevel')
        mock_Formatter = self.mock_patch_object(
            self.dom0_pluginlib.logging, 'Formatter')
        mock_sysh_setFormatter = self.mock_patch_object(
            self.dom0_pluginlib.logging.handlers.SysLogHandler, 'setFormatter')
        mock_Logger_addHandler = self.mock_patch_object(
            self.dom0_pluginlib.logging.Logger, 'addHandler')
        mock_socket = self.mock_patch_object(
            self.dom0_pluginlib.logging.handlers.SysLogHandler,
            '_connect_unixsocket')
        mock_path_exist.return_value = False

        self.dom0_pluginlib.configure_logging(name)

        self.assertTrue(mock_Logger_setLevel.called)
        self.assertFalse(mock_sysh_setLevel.called)
        self.assertFalse(mock_Formatter.called)
        self.assertFalse(mock_sysh_setFormatter.called)
        self.assertFalse(mock_Logger_addHandler.called)
        self.assertFalse(mock_socket.called)

    @mock.patch.object(os.path, 'exists')
    def test_configure_logging_log(self, mock_path_exist):
        name = 'fake_name'
        mock_Logger_setLevel = self.mock_patch_object(
            self.dom0_pluginlib.logging.Logger, 'setLevel')
        mock_sysh_setLevel = self.mock_patch_object(
            self.dom0_pluginlib.logging.handlers.SysLogHandler, 'setLevel')
        mock_Formatter = self.mock_patch_object(
            self.dom0_pluginlib.logging, 'Formatter')
        mock_sysh_setFormatter = self.mock_patch_object(
            self.dom0_pluginlib.logging.handlers.SysLogHandler, 'setFormatter')
        mock_Logger_addHandler = self.mock_patch_object(
            self.dom0_pluginlib.logging.Logger, 'addHandler')
        mock_socket = self.mock_patch_object(
            self.dom0_pluginlib.logging.handlers.SysLogHandler,
            '_connect_unixsocket')
        mock_path_exist.return_value = True

        self.dom0_pluginlib.configure_logging(name)

        self.assertTrue(mock_Logger_setLevel.called)
        self.assertTrue(mock_sysh_setLevel.called)
        self.assertTrue(mock_Formatter.called)
        self.assertTrue(mock_sysh_setFormatter.called)
        self.assertTrue(mock_Logger_addHandler.called)
        self.assertTrue(mock_socket.called)

    def test_exists_ok(self):
        fake_args = {'k1': 'v1'}
        self.assertEqual('v1', self.dom0_pluginlib.exists(fake_args, 'k1'))

    def test_exists_exception(self):
        fake_args = {'k1': 'v1'}
        self.assertRaises(self.dom0_pluginlib.ArgumentError,
                          self.dom0_pluginlib.exists,
                          fake_args,
                          'no_key')

    def test_optional_exist(self):
        fake_args = {'k1': 'v1'}
        self.assertEqual('v1',
                         self.dom0_pluginlib.optional(fake_args, 'k1'))

    def test_optional_none(self):
        fake_args = {'k1': 'v1'}
        self.assertIsNone(self.dom0_pluginlib.optional(fake_args,
                                                       'no_key'))

    def test_get_domain_0(self):
        mock_get_this_host = self.mock_patch_object(
            self.session.xenapi.session,
            'get_this_host',
            return_val='fake_host_ref')
        mock_get_vm_records = self.mock_patch_object(
            self.session.xenapi.VM,
            'get_all_records_where',
            return_val={"fake_vm_ref": "fake_value"})

        ret_value = self.dom0_pluginlib._get_domain_0(self.session)

        self.assertTrue(mock_get_this_host.called)
        self.assertTrue(mock_get_vm_records.called)
        self.assertEqual('fake_vm_ref', ret_value)

    def test_with_vdi_in_dom0(self):
        self.mock_patch_object(
            self.dom0_pluginlib,
            '_get_domain_0',
            return_val='fake_dom0_ref')
        mock_vbd_create = self.mock_patch_object(
            self.session.xenapi.VBD,
            'create',
            return_val='fake_vbd_ref')
        mock_vbd_plug = self.mock_patch_object(
            self.session.xenapi.VBD,
            'plug')
        self.mock_patch_object(
            self.session.xenapi.VBD,
            'get_device',
            return_val='fake_device_xvda')
        mock_vbd_unplug_with_retry = self.mock_patch_object(
            self.dom0_pluginlib,
            '_vbd_unplug_with_retry')
        mock_vbd_destroy = self.mock_patch_object(
            self.session.xenapi.VBD,
            'destroy')

        def handle_function(vbd):
            # the fake vbd handle function
            self.assertEqual(vbd, 'fake_device_xvda')
            self.assertTrue(mock_vbd_plug.called)
            self.assertFalse(mock_vbd_unplug_with_retry.called)
            return 'function_called'

        fake_vdi = 'fake_vdi'
        return_value = self.dom0_pluginlib.with_vdi_in_dom0(
            self.session, fake_vdi, False, handle_function)

        self.assertEqual('function_called', return_value)
        self.assertTrue(mock_vbd_plug.called)
        self.assertTrue(mock_vbd_unplug_with_retry.called)
        self.assertTrue(mock_vbd_destroy.called)
        args, kwargs = mock_vbd_create.call_args
        self.assertEqual('fake_dom0_ref', args[0]['VM'])
        self.assertEqual('RW', args[0]['mode'])

    def test_vbd_unplug_with_retry_success_at_first_time(self):
        self.dom0_pluginlib._vbd_unplug_with_retry(self.session,
                                                   'fake_vbd_ref')
        self.assertEqual(1, self.session.xenapi.VBD.unplug.call_count)

    def test_vbd_unplug_with_retry_detached_already(self):
        error = FakeUnplugException(['DEVICE_ALREADY_DETACHED'])

        self.session.xenapi.VBD.unplug.side_effect = error
        self.dom0_pluginlib.XenAPI.Failure = FakeUnplugException
        self.dom0_pluginlib._vbd_unplug_with_retry(self.session,
                                                   'fake_vbd_ref')
        self.assertEqual(1, self.session.xenapi.VBD.unplug.call_count)

    def test_vbd_unplug_with_retry_success_at_second_time(self):
        side_effects = [FakeUnplugException(['DEVICE_DETACH_REJECTED']),
                        None]

        self.session.xenapi.VBD.unplug.side_effect = side_effects
        self.dom0_pluginlib.XenAPI.Failure = FakeUnplugException
        self.dom0_pluginlib._vbd_unplug_with_retry(self.session,
                                                   'fake_vbd_ref')
        self.assertEqual(2, self.session.xenapi.VBD.unplug.call_count)

    @mock.patch.object(time, 'sleep')
    def test_vbd_unplug_with_retry_exceed_max_attempts(self, mock_sleep):
        side_effects = ([FakeUnplugException(['DEVICE_DETACH_REJECTED'])]
                        * (self.dom0_pluginlib.MAX_VBD_UNPLUG_RETRIES + 1))
        self.session.xenapi.VBD.unplug.side_effect = side_effects
        self.dom0_pluginlib.XenAPI.Failure = FakeUnplugException

        self.assertRaises(self.dom0_pluginlib.PluginError,
                          self.dom0_pluginlib._vbd_unplug_with_retry,
                          self.session, 'fake_vbd_ref')
        self.assertEqual(self.dom0_pluginlib.MAX_VBD_UNPLUG_RETRIES,
                         self.session.xenapi.VBD.unplug.call_count)
