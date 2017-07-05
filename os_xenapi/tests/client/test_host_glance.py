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

from os_xenapi.client import exception
from os_xenapi.client import host_glance
from os_xenapi.client import XenAPI
from os_xenapi.tests import base


class HostGlanceTestCase(base.TestCase):
    def test_upload_vhd(self):
        session = mock.Mock()
        num_retries = 'fake_num_retries'
        callback = 'fake_callback'
        retry_cb = 'fake_retry_cb'
        image_id = 'fake_image_id'
        sr_path = 'fake_sr_path'
        extra_headers = 'fake_extra_headers'
        vdi_uuids = 'fake_vdi_uuids'
        properties = {}
        args = {'image_id': image_id, 'sr_path': sr_path,
                'extra_headers': extra_headers, 'vdi_uuids': vdi_uuids,
                'properties': properties}
        host_glance.upload_vhd(session, num_retries, callback, retry_cb,
                               image_id, sr_path, extra_headers, vdi_uuids,
                               properties)
        session.call_plugin_serialized_with_retry.assert_called_with(
            'glance.py', 'upload_vhd2', num_retries, callback, retry_cb, **args
        )

    def test_upload_vhd_xenapi_failure_image_not_found(self):
        session = mock.Mock()
        num_retries = 'fake_num_retries'
        callback = 'fake_callback'
        retry_cb = 'fake_retry_cb'
        image_id = 'fake_image_id'
        sr_path = 'fake_sr_path'
        extra_headers = 'fake_extra_headers'
        vdi_uuids = 'fake_vdi_uuids'
        properties = {}
        args = {'image_id': image_id, 'sr_path': sr_path,
                'extra_headers': extra_headers, 'vdi_uuids': vdi_uuids,
                'properties': properties}

        session.call_plugin_serialized_with_retry.side_effect = XenAPI.Failure(
            ('XENAPI_PLUGIN_FAILURE', 'upload_vhd2',
             'PluginError', 'ImageNotFound')
        )
        self.assertRaises(exception.PluginImageNotFound,
                          host_glance.upload_vhd, session, num_retries,
                          callback, retry_cb, image_id, sr_path, extra_headers,
                          vdi_uuids, properties)

        session.call_plugin_serialized_with_retry.assert_called_with(
            'glance.py', 'upload_vhd2', num_retries, callback, retry_cb, **args
        )

    def test_upload_vhd_xenapi_failure_reraise(self):
        session = mock.Mock()
        num_retries = 'fake_num_retries'
        callback = 'fake_callback'
        retry_cb = 'fake_retry_cb'
        image_id = 'fake_image_id'
        sr_path = 'fake_sr_path'
        extra_headers = 'fake_extra_headers'
        vdi_uuids = 'fake_vdi_uuids'
        properties = {}
        args = {'image_id': image_id, 'sr_path': sr_path,
                'extra_headers': extra_headers, 'vdi_uuids': vdi_uuids,
                'properties': properties}

        session.call_plugin_serialized_with_retry.side_effect = XenAPI.Failure(
            ('untouch')
        )
        self.assertRaises(XenAPI.Failure, host_glance.upload_vhd, session,
                          num_retries, callback, retry_cb, image_id, sr_path,
                          extra_headers, vdi_uuids, properties)

        session.call_plugin_serialized_with_retry.assert_called_with(
            'glance.py', 'upload_vhd2', num_retries, callback, retry_cb, **args
        )
