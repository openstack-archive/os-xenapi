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


class NetworkingGCandPCITestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(NetworkingGCandPCITestCase, self).setUp()
        self.host = self.load_plugin("xenhost.py")
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")
        self.mock_patch_object(self.host,
                               '_run_command',
                               'fake_run_cmd_return')

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
        fake_cmd_result = "Currently running: Not True"
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

    def test_get_pci_type_with_domain(self):
        fake_pci_device = '0000:00:00.0'
        self.host._run_command.return_value = ['fake_pci_type', ]

        self.host.get_pci_type('fake_session', fake_pci_device)
        self.host._run_command.assert_called_with(
            ["ls", "/sys/bus/pci/devices/" + fake_pci_device + "/"])

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
