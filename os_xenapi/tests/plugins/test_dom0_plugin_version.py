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

from os_xenapi.tests.plugins import plugin_test


class Dom0PluginVersion(plugin_test.PluginTestBase):
    def setUp(self):
        super(Dom0PluginVersion, self).setUp()
        self.dom0_plugin_version = self.load_plugin('dom0_plugin_version.py')

    def test_dom0_plugin_version(self):
        session = 'fake_session'
        expected_value = self.dom0_plugin_version.PLUGIN_VERSION
        return_value = self.dom0_plugin_version.get_version(session)
        self.assertEqual(expected_value, return_value)
