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

"""
test_os_xenapi
----------------------------------

Tests for `os_xenapi` module.
"""

import mock

from os_xenapi.client import objects
from os_xenapi.tests import base


class XenAPISessionObjectTestCase(base.TestCase):
    def setUp(self):
        super(XenAPISessionObjectTestCase, self).setUp()
        self.session = mock.Mock()
        self.obj = objects.XenAPISessionObject(self.session, "FAKE")

    def test_call_method_via_attr(self):
        self.session.call_xenapi.return_value = "asdf"
        result = self.obj.get_X("ref")
        self.assertEqual(result, "asdf")
        self.session.call_xenapi.assert_called_once_with("FAKE.get_X", "ref")


class ObjectsTestCase(base.TestCase):
    def setUp(self):
        super(ObjectsTestCase, self).setUp()
        self.session = mock.Mock()

    def test_VM(self):
        vm = objects.VM(self.session)
        vm.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("VM.get_X", "ref")
