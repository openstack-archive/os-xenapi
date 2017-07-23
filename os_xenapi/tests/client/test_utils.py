# Copyright 2017 Citrix Systems
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

from eventlet import greenio
import os

from os_xenapi.client import exception
from os_xenapi.client import utils
from os_xenapi.tests import base


class UtilsTestCase(base.TestCase):
    def setUp(self):
        super(UtilsTestCase, self).setUp()
        self.session = mock.Mock()

    def test_get_default_sr(self):
        FAKE_POOL_REF = 'fake-pool-ref'
        FAKE_SR_REF = 'fake-sr-ref'
        pool = self.session.pool
        pool.get_all.return_value = [FAKE_POOL_REF]
        pool.get_default_SR.return_value = FAKE_SR_REF

        default_sr_ref = utils.get_default_sr(self.session)

        pool.get_all.assert_called_once_with()
        pool.get_default_SR.assert_called_once_with(FAKE_POOL_REF)
        self.assertEqual(default_sr_ref, FAKE_SR_REF)

    def test_get_default_sr_except(self):
        FAKE_POOL_REF = 'fake-pool-ref'
        FAKE_SR_REF = None
        mock_pool = self.session.pool
        mock_pool.get_all.return_value = [FAKE_POOL_REF]
        mock_pool.get_default_SR.return_value = FAKE_SR_REF

        self.assertRaises(exception.NotFound,
                          utils.get_default_sr,
                          self.session)

    def test_create_vdi(self):
        mock_create = self.session.VDI.create
        mock_create.return_value = 'fake-vdi-ref'
        fake_instance = {'uuid': 'fake-uuid'}
        expect_other_conf = {'nova_disk_type': 'fake-disk-type',
                             'nova_instance_uuid': 'fake-uuid'}
        fake_virtual_size = 1
        create_param = {
            'name_label': 'fake-name-label',
            'name_description': '',
            'SR': 'fake-sr-ref',
            'virtual_size': str(fake_virtual_size),
            'type': 'User',
            'sharable': False,
            'read_only': False,
            'xenstore_data': {},
            'other_config': expect_other_conf,
            'sm_config': {},
            'tags': [],
        }

        vdi_ref = utils.create_vdi(self.session, 'fake-sr-ref', fake_instance,
                                   'fake-name-label', 'fake-disk-type',
                                   fake_virtual_size)

        self.session.VDI.create.assert_called_once_with(create_param)
        self.assertEqual(vdi_ref, 'fake-vdi-ref')

    @mock.patch.object(os, 'pipe')
    @mock.patch.object(greenio, 'GreenPipe')
    def test_create_pipe(self, mock_green_pipe, mock_pipe):
        mock_pipe.return_value = ('fake-rpipe', 'fake-wpipe')
        mock_green_pipe.side_effect = ['fake-rfile', 'fake-wfile']

        rfile, wfile = utils.create_pipe()

        mock_pipe.assert_called_once_with()
        real_calls = mock_green_pipe.call_args_list
        expect_calls = [mock.call('fake-rpipe', 'rb', 0),
                        mock.call('fake-wpipe', 'wb', 0)]
        self.assertEqual(expect_calls, real_calls)
        self.assertEqual('fake-rfile', rfile)
        self.assertEqual('fake-wfile', wfile)

    def test_get_vdi_import_path(self):
        self.session.get_session_id.return_value = 'fake-id'
        task_ref = 'fake-task-ref'
        vdi_ref = 'fake-vdi-ref'
        expected_path = '/import_raw_vdi?session_id=fake-id&'
        expected_path += 'task_id=fake-task-ref&vdi=fake-vdi-ref&format=vhd'

        export_path = utils.get_vdi_import_path(self.session,
                                                task_ref,
                                                vdi_ref)

        self.session.get_session_id.assert_called_once_with()
        self.assertEqual(expected_path, export_path)

    def test_get_vdi_export_path(self):
        self.session.get_session_id.return_value = 'fake-id'
        task_ref = 'fake-task-ref'
        vdi_ref = 'fake-vdi-ref'
        expected_path = '/export_raw_vdi?session_id=fake-id&'
        expected_path += 'task_id=fake-task-ref&vdi=fake-vdi-ref&format=vhd'

        export_path = utils.get_vdi_export_path(self.session,
                                                task_ref,
                                                vdi_ref)

        self.session.get_session_id.assert_called_once_with()
        self.assertEqual(expected_path, export_path)
