# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os

from os_xenapi.tests import base


class PluginTestBase(base.TestCase):
    def test_build_suppack(self):
        test_path = os.path.dirname(__file__)
        relative_path = "../../dom0"
        for item in relative_path.split('/'):
            test_path = os.path.join(test_path, item)
        dom0_path = os.path.realpath(test_path)
        os.system('%s/suppack/build-xenserver-suppack.sh' % dom0_path)
        self.assertTrue(
            os.path.exists('%s/build/conntrack-tools.iso' % dom0_path))
        self.assertTrue(
            os.path.exists('%s/build/conntrack-tools.iso.md5' % dom0_path))
        self.assertTrue(
            os.path.exists('%s/build/conntrack-tools.metadata.md5'
                           % dom0_path))
        self.assertTrue(
            os.path.exists('%s/build/xenapi-plugins-upstream.iso' % dom0_path))
        self.assertTrue(
            os.path.exists('%s/build/xenapi-plugins-upstream.iso.md5'
                           % dom0_path))
        self.assertTrue(
            os.path.exists('%s/build/xenapi-plugins-upstream.metadata.md5'
                           % dom0_path))
