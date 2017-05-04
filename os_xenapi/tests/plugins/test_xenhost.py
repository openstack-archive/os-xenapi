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


class VDevOptTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(VDevOptTestCase, self).setUp()
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
