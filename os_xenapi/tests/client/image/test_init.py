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

from os_xenapi.client import image
from os_xenapi.client.image import vdi_handler
from os_xenapi.tests import base


class ImageTestCase(base.TestCase):
    def setUp(self):
        super(ImageTestCase, self).setUp()
        self.context = mock.Mock()
        self.session = mock.Mock()
        self.instance = {'name': 'instance-001'}
        self.host_url = "http://fake-host.com"
        self.stream = mock.Mock()

    @mock.patch.object(vdi_handler.ImageStreamToVDIs, 'start')
    def test_stream_to_vdis(self, mock_start):
        image.stream_to_vdis(self.context, self.session, self.instance,
                             self.host_url, self.stream)

        mock_start.assert_called_once_with()

    @mock.patch.object(vdi_handler.GenerateImageStream, 'get_image_data')
    def test_vdis_to_stream(self, mock_get):
        image.stream_from_vdis(self.context, self.session, self.instance,
                               self.host_url, ['fake-uuid'])

        mock_get.assert_called_once_with()
