# Copyright (c) 2017 OpenStack Foundation
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

from mock import call
import mock
from os_xenapi.tests.plugins import plugin_test
import re
import time


class FakeXenAPIException(Exception):
    pass


class FakeIOErrorException(Exception):
    pass


class Fake_AttributeError(Exception):
    pass

class FakePluginErrorException(Exception):
    def __init__(self, details):
        self.err = details


class FakeException(Exception)
    pass


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
        side_effect = ([FakePluginErrorException('Subprocess exception')])
        self.mock_patch_object(self.host.utils,
                               'run_command',
                               'fake_wrong_cmd_return')
        self.host.utils.run_command.side_effect = side_effect
        self.host.utils.SubprocessException = FakePluginErrorException

        self.assertRaises(self.pluginlib.PluginError,
                          self.host._run_command,
                          'fake_command')
        self.host.utils.run_command.assert_called_once()


class XenHostTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(XenHostTestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")
        self.mock_patch_object(self.host,
                               '_run_command')

    def test_resume_compute(self):
        self.mock_patch_object(self.session.xenapi.VM,
                               'start')
        self.host._resume_compute(self.session,
                                  'fake_compute_ref',
                                  'fake_compute_uuid')

        self.session.xenapi.VM.start.assert_called_once()

    def test_resume_compute_exception_compute_VM_restart(self):
        side_effect = FakeXenAPIException
        self.mock_patch_object(self.session.xenapi.VM,
                               'start')

        self.session.xenapi.VM.start.side_effect = side_effect
        self.host.XenAPI.Failure = FakeXenAPIException
        self.host._resume_compute(self.session,
                                  'fake_compute_ref',
                                  'fake_compute_uuid')

        self.session.xenapi.VM.start.assert_called_once()
        self.host._run_command.assert_called_with(
            ["xe", "vm-start", "uuid=%s" % 'fake_compute_uuid']
        )

    @mock.patch.object(time, 'sleep')
    def test_resume_compute_exception_wait_slave_available(self, mock_sleep):
        side_effect_xenapi_failure = FakeXenAPIException
        side_effect_plugin_error = [FakeXenAPIException("Wait for the slave \
                                                         to become available"),
                                    None]
        self.mock_patch_object(time,
                               'sleep')
        self.mock_patch_object(self.session.xenapi.VM,
                               'start')

        self.session.xenapi.VM.start.side_effect = \
            side_effect_xenapi_failure
        self.host.XenAPI.Failure = FakeXenAPIException

        self.host._run_command.side_effect = side_effect_plugin_error
        self.pluginlib.PluginError = FakePluginErrorException

        self.assertRaises((self.host.XenAPI.Failure,
                          self.pluginlib.PluginError),
                          self.host._resume_compute,
                          self.session,
                          'fake_compute_ref',
                          'fake_compute_uuid')

        self.session.xenapi.VM.start.assert_called_once()
        self.host._run_command.assert_called_with(
            ["xe", "vm-start", "uuid=%s" % 'fake_compute_uuid']
        )

    @mock.patch.object(time, 'sleep')
    def test_resume_compute_exception_unrecoverable(self, mock_sleep):
        side_effect_xenapi_failure = FakeXenAPIException
        side_effect_plugin_error = (
            [FakeXenAPIException(
                "Wait for the slave "
                "to become available")]
            * self.host.DEFAULT_TRIES)
        self.mock_patch_object(time,
                               'sleep')
        self.mock_patch_object(self.session.xenapi.VM,
                               'start')

        self.session.xenapi.VM.start.side_effect = \
            side_effect_xenapi_failure
        self.host.XenAPI.Failure = FakeXenAPIException

        self.host._run_command.side_effect = side_effect_plugin_error
        self.pluginlib.PluginError = FakePluginErrorException

        self.assertRaises((self.host.XenAPI.Failure,
                          [self.pluginlib.PluginError] *
                          (self.host.DEFAULT_TRIES + 1)),
                          self.host._resume_compute,
                          self.session,
                          'fake_compute_ref',
                          'fake_compute_uuid')

        self.session.xenapi.VM.start.assert_called_once()
        self.host._run_command.assert_called_with(
            ["xe", "vm-start", "uuid=%s" % 'fake_compute_uuid']
        )

    def test_set_host_enabled_no_enabled_key_in_arg_dict(self):
        temp_dict = {}
        temp_dict.pop('enabled', None)
        self.pluginlib.PluginError = FakeXenAPIException

        self.assertRaises(self.pluginlib.PluginError,
                          self.host.set_host_enabled,
                          self.host, temp_dict)

    def test_set_host_enabled_host_enable_disable_cmd_return_non_empty(self):
        temp_dict = {}
        temp_dict.update({'enabled': 'true'})
        temp_dict.update({'host_uuid': 'fake_host_uuid'})
        fake_run_command_return = 'none empty'
        self.mock_patch_object(self.host,
                               '_run_command',
                               fake_run_command_return)
        self.pluginlib.PluginError = FakePluginErrorException

        self.assertRaises(self.pluginlib.PluginError,
                          self.host.set_host_enabled,
                          self.host, temp_dict)

    def test_set_host_enabled_request_host_enabled(self):
        temp_dict = {}
        side_effects = ['', 'any_value']
        temp_dict.update({'enabled': 'true'})
        temp_dict.update({'host_uuid': 'fake_host_uuid'})
        self.mock_patch_object(self.host,
                               '_run_command',
                               ['', 'any_value'])
        expected = [call(['xe', 'host-enable', 'uuid=fake_host_uuid']),
                    call(['xe', 'host-param-get', 'uuid=fake_host_uuid', 'param-name=enabled'])]
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
        self.mock_patch_object(self.host,
                               '_run_command')
        self.host._run_command.side_effect = side_effects

        host_enabled = self.host.set_host_enabled(self.host, temp_dict)
        self.assertEqual(host_enabled, '{"status": "enabled"}')

    def test_set_host_enabled_confirm_host_disabled(self):
        temp_dict = {}
        side_effects = ['', 'any_value']
        temp_dict.update({'enabled': 'false'})
        temp_dict.update({'host_uuid': 'fake_host_uuid'})
        self.mock_patch_object(self.host,
                               '_run_command')
        self.host._run_command.side_effect = side_effects

        host_enabled = self.host.set_host_enabled(self.host, temp_dict)
        self.assertEqual(host_enabled, '{"status": "disabled"}')

    @mock.patch.object('close')
    @mock.patch.object('file')
    def test_writ_config_dict(self, mock_file, mock_close):
        temp_dict = {}
        mock_file.return_value = 'fake_file_return'
        mock_close.return_value = 'fake_file_close_return'
        self.host._write_config_dict(temp_dict)
        json.dump.assert_called_with(temp_dict, 'fake_file_return');
        mock_file.assert_called_with(self.host.config_file_path, 'w')
        mock_close.assert_called_once()

#need check
#need move test_writ_config_dict to another function
    def test_get_config_dict(self):
        self.mock_patch_object(self.host,
                               'file',
                               'fake_file_return')
        self.mock_patch_object(self.host,
                               'close',
                               'fake_file_close_return')
        config_dict = self.host._get_config_dict()
        expected = json.load("fake_file_return")
        self.assertEqual(expected, config_dict)

#need check, who will throw this exception?
#should IOError be self.IOError?
    def test_get_config_dict_IOError(self):
        side_effect = [FakeIOErrorException()]
        self.mock_patch_object(self.host,
                               'file',
                               'fake_file_return')
        self.mock_patch_object(self.host,
                               '_write_config_dict',
                               'fake_write_config_dict_return')
        self.mock_patch_object(self.host,
                               'close',
                               'fake_file_close_return')
        self.file.side_effect = side_effect
        self.IOError = FakeIOErrorException

        self.assertRaises(self.IOError,
                          self.host._get_config_dict)
        self.host._write_config_dict.assert_called_with({})

    @mock.patch.object(file, 'get', None)
    def test_get_config_no_config_key(self, mock_file_get):
        temp_dict = {}
        temp_dict.update({"params": 'fake_params'})
        temp_dict.update({"key": 'fake_key'})
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               'fake_get_config_dict_return')
        expected = self.host.get_config(self.host, FAKE_ARG_DICT)
        self.assertEqual(expected, "None")
        self.file.get.assert_called_with(temp_dict["key"])

    @mock.patch.object(file, 'get', "NotNone")
    def test_get_config_config_key_not_none(self, mock_file_get):
        temp_dict = {}
        temp_dict.update({"params": 'fake_params'})
        temp_dict.update({"key": 'fake_key'})
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               'fake_get_config_dict_return')
        expected = self.host.get_config(self.host, FAKE_ARG_DICT)
        self.assertEqual(expected, "NotNone")
        self.file.get.assert_called_with(temp_dict["key"])

    @mock.patch.object(json, 'loads')
    def test_get_config_json_load_exception(self, mock_json_loads):
        side_effect = [FakeException()]
        temp_dict = {}
        temp_dict.update({"params": 'fake_params'})
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               'fake_get_config_dict_return')
        Exception = FakeException
        mock_json_loads.side_effect = side_effect

        self.assertRaises(Exception,
                          self.host.get_config,
                          self.host, temp_dict)
        mock_json_loads.assert_called_with(temp_dict["params"])

    @mock.patch.object(json, 'loads')
    def test_set_config_remove_none_key(self, mock_json_loads):
        temp_arg_dict = {}
        temp_arg_dict.update({"params": 'fake_params'})
        temp_dict = {"key": "fake_key", "value": None}
        mock_json_loads.return_value = temp_dict
        tem_conf = {temp_dict["key"]: "fake_key"}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               temp_conf)
        self.mock_patch_object(self.host,
                               '_write_config_dict',
                               'fake_write_config_dict_return')

        self.host.set_config(self.host, temp_arg_dict)
        self.assertTrue("value" not in temp_dict)
        self.host._get_config_dict.assert_called_once()
        temp_conf.pop(key, None)
        self.host._write_config_dict.assert_called_with(temp_conf)

    @mock.patch.object(json, 'loads')
    def test_set_config_overwrite_key_value(self, mock_json_loads):
        temp_arg_dict = {}
        temp_arg_dict.update({"params": 'fake_params'})
        temp_dict = {"key": "fake_key", "value": "not_none"}
        mock_json_loads.return_value = temp_dict
        tem_conf = {temp_dict["key"]: "fake_key"}
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               temp_conf)
        self.mock_patch_object(self.host,
                               '_write_config_dict',
                               'fake_write_config_dict_return')

        self.host.set_config(self.host, temp_arg_dict)
        self.assertTrue("value" not in temp_dict)
        self.host._get_config_dict.assert_called_once()
        temp_conf.update({temp_dict["key"]: temp_dict["value"]})
        self.host._write_config_dict.assert_called_with(temp_conf)

    @mock.patch.object(json, 'loads')
    def test_iptables_config(self, mock_json_loads):
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               'iptables-save')
        self.mock_patch_object(self.pluginlib,
                               'optional',
                               'fake_cmd_pro_input')
        self.mock_patch_object(self.host,
                               '_run_command',
                               'fake_run_cmd_resule')
        expected = json.dumps(dict(out='fake_run_cmd_resule', err=''))

        ret_str = self.host.iptables_config(self.host.session, 'fake_args')
        self.pluginlib.exists.assert_called_once()
        self.pluginlib.optional.assert_called_once()
        mock_json_loads.assert_called_with('fake_cmd_args')
        self.assertEqual(ret_str, expected)

    @mock.patch.object(json, 'loads')
    def test_iptables_config_plugin_error(self, mock_json_loads):
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.mock_patch_object(self.pluginlib,
                               'optional',
                               'fake_cmd_pro_input')
        Exception = FakeException;

        self.assertRaises(Exception,
                          self.host.iptables_config,
                          self.host.session, 'fake_args')
        self.pluginlib.exists.assert_called_once()
        self.pluginlib.optional.assert_called_once()
        mock_json_loads.assert_called_with(None)

    def test_ovs_add_patch_port(self):
        brige_name = 'fake_brige_name'
        port_name = 'fake_port_name'
        peer_port_name = 'fake_peer_port_name'
        side_effects = [brige_name, port_name, peer_port_name]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists', 'del-port',
                             port_name, '--', 'add-port', brige_name,
                             'fake_port_name', '--', 'set', 'interface',
                             'fake_port_name', 'type=patch', 
                             'options:peer=%s' % peer_port_name]

        self.host._ovs_add_patch_port('fake_args')
        self.pluginlib.exists.assert_called_once()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ovs_del_port(self):
        brige_name = 'fake_brige_name'
        port_name = 'fake_port_name'
        side_effects = [brige_name, port_name]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists', 'del-port',
                             bridge_name, port_name]

        self.host._ovs_del_port('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ovs_del_br(self):
        brige_name = 'fake_brige_name'
        self.mock_patch_object(self.host,
                               '_run_command')
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               brige_name)
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists',
                             'del-br', bridge_name]

        self.host._ovs_add_patch_port('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ovs_set_if_external_id(self):
        interface = 'fake_interface'
        extneral_id = 'fake_extneral_id'
        value = 'fake_value'
        side_effects = [interface, extneral_id, value]
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', 'set', 'Interface', interface,
                             'external-ids:%s=%s' % (extneral_id, value)]

        self.host._ovs_set_if_external_id('fake_args')
        self.pluginlib.exists.assert_called_once()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ovs_add_port(self):
        brige_name = 'fake_brige_name'
        port_name = 'fake_port_name'
        side_effects = [brige_name, port_name]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists', 'del-port', port_name,
                             '--', 'add-port', bridge_name, port_name]

        self.host._ovs_add_port('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ovs_create_port(self):
        brige_name = 'fake_brige_name'
        port_name = 'fake_port_name'
        iface_id = 'fake_iface_id'
        mac = 'fake_mac'
        status = 'fake_status'
        side_effects = [brige_name, port_name, iface_id, mac, status]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ovs-vsctl', '--', '--if-exists', 'del-port', port,
                             '--', 'add-port', bridge, port,
                             '--', 'set', 'Interface', port,
                             'external_ids:iface-id=%s' % iface_id,
                             'external_ids:iface-status=%s' % status,
                             'external_ids:attached-mac=%s' % mac,
                             'external_ids:xs-vif-uuid=%s' % iface_id]

        self.host._ovs_create_port('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ip_link_get_dev(self):
        device_name = 'fake_device_name'
        expected_cmd_args = ['ip', 'link', 'show', device_name]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               brige_name)

        self.host._ip_link_get_dev('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ip_link_del_dev(self);
        device_name = 'fake_device_name'
        expected_cmd_args = ['ip', 'link', 'delete', device_name]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               brige_name)

        self.host._ip_link_del_dev('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ip_link_add_veth_pair(self):
        dev1_name = 'fake_brige_name'
        dev2_name = 'fake_port_name'
        side_effects = [dev1_name, dev2_name]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ip', 'link', 'add', dev1_name, 'type',
                             'veth', 'peer', 'name', dev2_name]

        self.host._ip_link_add_veth_pair('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ip_link_set_dev(self):
        device_name = 'fake_device_name'
        option = 'fake_option'
        side_effects = [device_name, option]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ip', 'link', 'set', device_name, option]

        self.host._ip_link_set_dev('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_ip_link_set_promisc(self):
        device_name = 'fake_device_name'
        option = 'fake_option'
        side_effects = [device_name, option]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['ip', 'link', 'set', device_name, 'promisc', option]

        self.host.ip_link_set_promisc('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_brctl_add_br(self):
        bridge_name = 'fake_device_name'
        cmd_args = 'fake_option'
        side_effects = [bridge_name, cmd_args]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['brctl', 'addbr', bridge_name]

        self.host._brctl_add_br('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_brctl_del_br(self):
        brige_name = 'fake_brige_name'
        self.mock_patch_object(self.host,
                               '_run_command')
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               brige_name)
        expected_cmd_args = ['brctl', 'delbr', bridge_name]

        self.host.brctl_del_br('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_brctl_set_fd(self):
        bridge_name = 'fake_device_name'
        fd = 'fake_fd'
        side_effects = [bridge_name, fd]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['brctl', 'setfd', bridge_name, fd]

        self.host.brctl_set_fd('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_brctl_set_stp(self):
        bridge_name = 'fake_device_name'
        option = 'fake_option'
        side_effects = [bridge_name, option]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['brctl', 'stp', bridge_name, option]

        self.host._brctl_set_stp('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_brctl_add_if(self):
        bridge_name = 'fake_device_name'
        if_name = 'fake_if_name'
        side_effects = [bridge_name, if_name]
        self.mock_patch_object(self.host,
                               '_run_command')
        self.pluginlib.exists.side_effect = side_effects
        expected_cmd_args = ['brctl', 'delif', bridge_name, if_name]

        self.host._brctl_add_if('fake_args')
        self.pluginlib.exists.assert_called()
        self.host._run_command.assert_called_with(expected_cmd_args)

    def test_network_config_invalid_cmd(self):
        fake_invalid_cmd = 0
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               fake_invalid_cmd)
        pluginlib.PluginError = FakePluginErrorException

        self.assertRaises(pluginlib.PluginError,
                          self.host.network_config,
                          'fake_session', 'fake_args')
        self.pluginlib.assert_called_with('fake_args', 'cmd')

    def test_network_config_unexpected_cmd(self):
        fake_unexpected_cmd = 'fake_unknow_cmd'
        self.mock_patch_object(self.pluginlib,
                               'exists',
                               fake_unexpected_cmd)
        pluginlib.PluginError = FakePluginErrorException

        self.assertRaises(pluginlib.PluginError,
                          self.host.network_config,
                          'fake_session', 'fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'cmd')

#take one function 'ovs_add_patch_port' in the cmd table to check
    def test_network_config(self):
        fake_valid_cmd = 'ovs_add_patch_port'
        side_effects = ['ovs_add_patch_port', 'fake_cmd_args']
        self.mock_patch_object(self.pluginlib,
                               'exists')
        self.pluginlib.exists.side_effect = side_effects
        self.mock_patch_object(self.host,
                               '_ovs_add_patch_port',
                               'fake_add_port_return')

        self.host.network_config('fake_session', 'fake_args')
        self.pluginlib.exists.assert_called_with('fake_args', 'cmd')
        self.host._ovs_add_patch_port.assert_called_with(
            'fake_add_port_return')

#may be removed because the operation would be deprecate
    def test_power_action_disable_cmd_result_not_empty(self):
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        self.mock_patch_object(self.host,
                               '_run_command',
                               'not_empty')
        pluginlib.PluginError = FakePluginErrorException
        expected_cmd_arg = ["xe", "host-disable", "uuid=%s" %
                            'fake_host_uuid']
        expected_cmd_result = 'not_empty'

        self.assertRaises(pluginlib.PluginError,
                          self.host._power_action,
                          'fake_action', temp_arg_dict)
        self.host._run_command.assert_called_with(expected_cmd_arg)

#may be removed because the operation would be deprecate
    def test_power_action_shutdown_cmd_result_not_empty(self):
        side_effects = [None, 'not_empty']
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        self.host._run_command.side_effect = side_effects;
        pluginlib.PluginError = FakePluginErrorException
        expected_cmd_arg_list = [call(["xe", "host-disable", "uuid=%s" 
                                  % host_uuid]),
                                 call(["xe", "vm-shutdown", "--multiple",
                                   "resident-on=%s" % host_uuid])]

        self.assertRaises(pluginlib.PluginError,
                          self.host._power_action,
                          'fake_action', temp_arg_dict)
        self.assertEqual(self.host._run_command.call_args_list,
                         expected_cmd_arg_list)

#may be removed because the operation would be deprecate
    def test_power_action_input_cmd_result_not_empty(self):
        side_effects = [None, None, 'not_empty']
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        self.host._run_command.side_effect = side_effects;
        pluginlib.PluginError = FakePluginErrorException
        cmds = {"reboot": "host-reboot",
                "startup": "host-power-on",
                "shutdown": "host-shutdown"}
        fake_action = 'reboot' # 'statup' and 'shutdown' should be same
        expected_cmd_arg_list = [call(["xe", "host-disable", "uuid=%s" 
                                      % host_uuid]),
                                 call(["xe", "vm-shutdown", "--multiple",
                                      "resident-on=%s" % host_uuid]),
                                 call(["xe", cmds[fake_action], "uuid=%s" %
                                      host_uuid])]

        self.assertRaises(pluginlib.PluginError,
                          self.host._power_action,
                          fake_action, temp_arg_dict)
        self.assertEqual(self.host._run_command.call_args_list,
                         expected_cmd_arg_list)

    def test_power_action(self):
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        self.mock_patch_object(self.host,
                               '_run_command',
                               None)
        cmds = {"reboot": "host-reboot",
                "startup": "host-power-on",
                "shutdown": "host-shutdown"}
        fake_action = 'reboot' # 'statup' and 'shutdown' should be same
        expected_cmd_arg_list = [call(["xe", "host-disable", "uuid=%s" 
                                      % host_uuid]),
                                 call(["xe", "vm-shutdown", "--multiple",
                                      "resident-on=%s" % host_uuid]),
                                 call(["xe", cmds[fake_action], "uuid=%s" %
                                      host_uuid])]
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
        action_result = self.host.host_reboot(fake_action, 'fake_arg_dict')

        self.host._power_action.assert_called_with('reboot', 'fake_arg_dict')
        self.assertEqual(action_result, 'fake_action_result')

    def test_host_shutdown(self):
        fake_action = 'shutdown'
        self.mock_patch_object(self.host,
                               '_power_action',
                               'fake_action_result')
        action_result = self.host.host_reboot(fake_action, 'fake_arg_dict')

        self.host._power_action.assert_called_with('shutdown', 'fake_arg_dict')
        self.assertEqual(action_result, 'fake_action_result')

    def test_host_startup(self):
        fake_action = 'startup'
        self.mock_patch_object(self.host,
                               '_power_action',
                               'fake_action_result')
        action_result = self.host.host_reboot(fake_action, 'fake_arg_dict')

        self.host._power_action.assert_called_with('startup', 'fake_arg_dict')
        self.assertEqual(action_result, 'fake_action_result')

    def test_host_join(self):
        temp_arg_dict = {'master_addr': 'fake_master_addr',
                         'master_user': 'fake_master_user',
                         'master_pass': 'fake_master_pass',
                         'compute_uuid': 'fake_compute_uuid'}
        self.mock_patch_object(self.XenAPI,
                               'Session',
                               'fake_session')
        self.mock_patch_object(self.session.xenapi.VM,
                               'get_by_uuid',
                               'fake_compute_ref')
        self.mock_patch_object(self.session.xenapi.VM,
                               'clean_shutdown')
        self.mock_patch_object(self.session.xenapi.pool,
                               'join')
        self.mock_patch_object(self.host,
                               '_resume_compute')

        self.host.host_join(self.host, temp_arg_dict)
        self.session.xenapi.pool.join.assert_called_with(
            temp_arg_dict.get("master_addr"),
            temp_arg_dict.get("master_user"),
            temp_arg_dict.get("master_pass"))
        self.host._resume_compute.assert_called_with(
            'fake_session', 'fake_compute_ref',
            temp_arg_dict.get("compute_uuid"))

    def test_host_join_force_join(self):
        temp_arg_dict = {'master_addr': 'fake_master_addr',
                         'master_user': 'fake_master_user',
                         'master_pass': 'fake_master_pass',
                         'compute_uuid': 'fake_compute_uuid'}
        self.mock_patch_object(self.XenAPI,
                               'Session',
                               'fake_session')
        self.mock_patch_object(self.session.xenapi.VM,
                               'get_by_uuid',
                               'fake_compute_ref')
        self.mock_patch_object(self.session.xenapi.VM,
                               'clean_shutdown')
        self.mock_patch_object(self.session.xenapi.pool,
                               'join_force')
        self.mock_patch_object(self.host,
                               '_resume_compute')

        self.host.host_join(self.host, temp_arg_dict)
        self.session.xenapi.pool.join_force.assert_called_with(
            temp_arg_dict.get("master_addr"),
            temp_arg_dict.get("master_user"),
            temp_arg_dict.get("master_pass"))
        self.host._resume_compute.assert_called_with(
            'fake_session', 'fake_compute_ref',
            temp_arg_dict.get("compute_uuid"))

    def test_host_data(self):
        temp_arg_dict = {'host_uuid': 'fake_host_uuid'}
        fake_ret_dict = {}
        fake_config_setting = {'config': 'fake_config_setting'}
        expected_ret_dict = fake_ret_dict.update(
            fake_config_setting)
        self.mock_patch_object(self.host,
                               '_run_command',
                               'fake_resp')
        self.mock_patch_object(self.host,
                               'parse_response',
                               'fake_parsed_data')
        self.mock_patch_object(self.host,
                               'cleanup',
                               fake_ret_dict)
        self.mock_patch_object(self.host,
                               '_get_config_dict',
                               fake_config_setting)

        return_host_data = self.host.host_data(self.host,
            temp_arg_dict)
        self.host._run_command.assert_called_with(["xe",
            "host-param-list", "uuid=%s" % temp_arg_dict['host_uuid']])
        self.host.parse_response.assert_called_with('fake_resp')
        self.host.cleanup('fake_parsed_data')
        self.host._get_config_dict.assert_called_once()
        self.assertEqual(expected_ret_dict, return_host_data)


    def test_parse_response(self):
        fake_resp = 'fake_name ( fake_flag): fake_value'
        expected_data = {'fake_name': 'fake_value'}

        result_data = self.host.parse_response(fake_resp)
        self.assertEqual(result_data, expected_data)

    @mock.patch.object(re, 'match')
    def test_parse_response_invalid_line(self, mock_re_match):
        side_effect = [Fake_AttributeError()]
        fake_resp = 'fake_name ( fake_flag): fake_value'
        expected_data = {}
        AttributeError = Fake_AttributeError
        mock_re_match.side_effect = side_effect
        
        result_data = self.host.parse_response(fake_resp)
        self.assertEqual(result_data, expected_data)

    def test_host_uptime(self):
        self.mock_patch_object(self.host,
                               '_run_command',
                               'fake_uptime')
        uptime_return = self.host.host_uptime(self.host, 'fake_arg_dict')

        self.assertEqual(uptime_return, {'uptime': 'fake_uptime'})

    def test_query_gc_running(self):
        fake_cmd_result = "Currently running: True"
        self.mock_patch_object(self.host,
                               '_run_command',
                               fake_cmd_result)
        query_gc_result = self.host.query_gc('fake_session',
            'fake_sr_uuid', 'fake_vdi_uuid')
        self.assertTrue(query_gc_result)
        self.host._run_command.assert_called_with(
            ["/opt/xensource/sm/cleanup.py",
            "-q", "-u", 'fake_vdi_uuid'])

    def test_query_gc_not_running(self):
        fake_cmd_result = "Currently running: Not True"
        self.mock_patch_object(self.host,
                               '_run_command',
                               fake_cmd_result)
        query_gc_result = self.host.query_gc('fake_session',
            'fake_sr_uuid', 'fake_vdi_uuid')
        self.assertNotTrue(query_gc_result)
        self.host._run_command.assert_called_with(
            ["/opt/xensource/sm/cleanup.py",
            "-q", "-u", 'fake_vdi_uuid'])

    def test_get_pci_device_details(self):
        self.mock_patch_object(self.host,
                               '_run_command')
        self.host.get_pci_device_details('fake_session')
        self.host._run_command.assert_called_with(
            ["lspci", "-vmmnk"])

    def test_get_pci_type_no_domain(self):
        fake_pci_device = '00:00.0'
        self.mock_patch_object(self.host,
                               '_run_command')

        self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + '0000:' + pci_device + "/"])

    def test_get_pci_type_with_domain(self):
        fake_pci_device = '0000:00:00.0'
        self.mock_patch_object(self.host,
                               '_run_command')

        self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + pci_device + "/"])

    def test_get_pci_type_physfn(self):
        fake_pci_device = '0000:00:00.0'
        self.mock_patch_object(self.host,
                               '_run_command',
                               'physfn')

        output = self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + pci_device + "/"])
        self.assertEqual(output, 'type-VF')

    def test_get_pci_type_virtfn(self):
        fake_pci_device = '0000:00:00.0'
        self.mock_patch_object(self.host,
                               '_run_command',
                               'virtfn')

        output = self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + pci_device + "/"])
        self.assertEqual(output, 'type-PF')

    def test_get_pci_type_PCI(self):
        fake_pci_device = '0000:00:00.0'
        self.mock_patch_object(self.host,
                               '_run_command',
                               'other')

        output = self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + pci_device + "/"])
        self.assertEqual(output, 'type-PCI')

'''
#issue with the source code, need confirm the fix
    def test_clean_up(self):
        fake_arg_dict = {
            'enabled': 'enabled',
            'memory-total': '0',
            'memory-overhead': '1',
            'memory-free': '2',
            'memory-free-computed': '3',
            'enabled': False,
            'uuid': 'fake_uuid',
            'name-label': 'fake_name-label',
            'name-description': 'fake_name-description',
            'hostname': 'fake_hostname',
            'address': 'fake_address',
            'other-config': 'fake_other-config_1; fake_other-config_2',
            'capabilities': 'fake_cap_1; fake_cap_2',
            'cpu_info': 'cpu_count:1; family:101; unknow:1'
        }
        expected_out = {
            'enabled': 'enabled',
            'memory-total': '0',
            'memory-overhead': '1',
            'memory-free': '2',
            'memory-free-computed': '3',
            'enabled': False,
            'uuid': 'fake_uuid',
            'name-label': 'fake_name-label',
            'name-description': 'fake_name-description',
            'hostname': 'fake_hostname',
            'address': 'fake_address',
            'other-config': 'fake_other-config_1; fake_other-config_2',
            'capabilities': 'fake_cap_1; fake_cap_2',
            'cpu_info': 'cpu_count:1; family:101; unknow:1'
        }

        out = self.host.cleanup(fake_ret_dict)
        self.assertEqual(out, )

# skip this case temporarily because of grammatical errors in
# xenhost.py
    def test_set_host_enabled_unexpected_enabled_key(self)
        FAKE_ARG_DICT.update({'enabled', 'unexpected'})
        self.host.sethost_enabled(self.host,
                                  FAKE_ARG_DICT)
        self.pluginlib.PluginError = \
            FakePluginErrorException(
                "Illegal enabled status: %s" % FAKE_ARG_DICT.get('enabled')
                )

        self.assertRaises(self.pluginlib.PluginError,
                          self.host.sethost_enabled,
                          self.host, FAKE_ARG_DICT)
'''
