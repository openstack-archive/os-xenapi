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

import eventlet
from six.moves import http_client as httplib
import tarfile


from os_xenapi.client import exception
from os_xenapi.client.image import vdi_handler
from os_xenapi.client.image import vhd_utils
from os_xenapi.client import utils
from os_xenapi.tests import base


class ImageStreamToVDIsTestCase(base.TestCase):
    def setUp(self):
        super(ImageStreamToVDIsTestCase, self).setUp()
        self.context = mock.Mock()
        self.session = mock.Mock()
        self.instance = {'name': 'instance-001'}
        self.host_url = "http://fake-host.com"
        self.stream = mock.Mock()

    @mock.patch.object(tarfile, 'open')
    @mock.patch.object(vhd_utils, 'VHDFileParser')
    @mock.patch.object(vdi_handler.ImageStreamToVDIs, '_createVDI',
                       return_value=('fake_sr_ref', 'fake_vdi_ref'))
    @mock.patch.object(vdi_handler.ImageStreamToVDIs, '_vhd_stream_to_vdi')
    def test_start(self, mock_to_vdi, mock_createVDI,
                   mock_get_parser, mock_open):
        self.session.task.create.return_value = 'fake-task-ref'
        mock_footer = mock.Mock(current_size=1073741824)
        mock_parser = mock.Mock()
        mock_get_parser.return_value = mock_parser
        mock_parser.parse_vhd_footer.return_value = mock_footer
        fake_vhd_info = mock.Mock()
        fake_vhd_info.size = 29371904
        fake_vhd_info.name = '0.vhd'
        mock_tarfile = mock.MagicMock()
        mock_tarfile.__enter__.return_value = mock_tarfile
        mock_tarfile.__iter__.return_value = [fake_vhd_info]
        mock_open.return_value = mock_tarfile
        mock_tarfile.extractfile.return_value = 'fake-file-obj'

        image_cmd = vdi_handler.ImageStreamToVDIs(self.context, self.session,
                                                  self.instance, self.host_url,
                                                  self.stream)
        image_cmd.start()

        self.session.task.create.assert_called_once_with(
            'VDI_IMPORT_for_instance-001',
            'Importing VDI for instance: instance-001')
        mock_open.assert_called_once_with(mode="r|gz", fileobj=self.stream)
        mock_tarfile.extractfile.assert_called_once_with(fake_vhd_info)
        mock_createVDI.assert_called_once_with(self.session, self.instance,
                                               1073741824)
        mock_to_vdi.assert_called_once_with(mock_parser, 'fake_vdi_ref',
                                            29371904)
        self.session.VDI.get_uuid.assert_called_once_with('fake_vdi_ref')

    @mock.patch.object(utils, 'get_default_sr',
                       return_value='fake-sr-ref')
    @mock.patch.object(utils, 'create_vdi',
                       return_value='fake-vdi-ref')
    def test_createVDI(self, mock_create_vdi, mock_get_sr):
        virtual_size = 1073741824
        image_cmd = vdi_handler.ImageStreamToVDIs(self.context, self.session,
                                                  self.instance, self.host_url,
                                                  self.stream)
        expect_result = ('fake-sr-ref', 'fake-vdi-ref')

        result = image_cmd._createVDI(self.session, self.instance,
                                      virtual_size)

        mock_get_sr.assert_called_once_with(self.session)
        mock_create_vdi.assert_called_once_with(self.session, 'fake-sr-ref',
                                                self.instance, 'instance-001',
                                                'root', virtual_size)
        self.session.VDI.get_uuid.assert_called_once_with('fake-vdi-ref')
        self.assertEqual(expect_result, result)

    @mock.patch.object(utils, 'get_vdi_import_path',
                       return_value='fake-path')
    @mock.patch.object(httplib.HTTPConnection, 'connect')
    @mock.patch.object(httplib.HTTPConnection, 'request')
    @mock.patch.object(httplib.HTTPConnection, 'send')
    @mock.patch.object(httplib.HTTPConnection, 'getresponse')
    @mock.patch.object(httplib.HTTPConnection, 'close')
    def test_vhd_stream_to_vdi(self, conn_close, conn_getRes, conn_send,
                               conn_req, conn_connect, get_path):
        vdh_stream = mock.Mock()
        cache_size = 4 * 1024
        remain_size = vdi_handler.CHUNK_SIZE / 2
        file_size = cache_size + vdi_handler.CHUNK_SIZE * 2 + remain_size
        headers = {'Content-Type': 'application/octet-stream',
                   'Content-Length': '%s' % file_size}
        image_cmd = vdi_handler.ImageStreamToVDIs(self.context, self.session,
                                                  self.instance, self.host_url,
                                                  self.stream)
        mock_parser = mock.Mock()
        mock_parser.cached_buff = b'\x00' * cache_size
        mock_parser.src_file = vdh_stream
        image_cmd.task_ref = 'fake-task-ref'
        vdh_stream.read.side_effect = ['chunk1', 'chunk2', 'chunk3']

        image_cmd._vhd_stream_to_vdi(mock_parser, 'fake_vdi_ref', file_size)

        conn_connect.assert_called_once_with()
        get_path.assert_called_once_with(self.session, 'fake-task-ref',
                                         'fake_vdi_ref')
        conn_connect.assert_called_once_with()
        conn_req.assert_called_once_with('PUT', 'fake-path', headers=headers)
        expect_send_calls = [mock.call(mock_parser.cached_buff),
                             mock.call('chunk1'),
                             mock.call('chunk2'),
                             mock.call('chunk3'),
                             ]
        conn_send.assert_has_calls(expect_send_calls)
        conn_getRes.assert_called_once_with()
        conn_close.assert_called_once_with()

    @mock.patch.object(utils, 'get_vdi_import_path',
                       return_value='fake-path')
    @mock.patch.object(httplib.HTTPConnection, 'connect')
    @mock.patch.object(httplib.HTTPConnection, 'request',
                       side_effect=Exception)
    @mock.patch.object(httplib.HTTPConnection, 'send')
    @mock.patch.object(httplib.HTTPConnection, 'getresponse')
    @mock.patch.object(httplib.HTTPConnection, 'close')
    def test_vhd_stream_to_vdi_put_except(self, conn_close, conn_getRes,
                                          conn_send, conn_req, conn_connect,
                                          get_path):
        vdh_stream = mock.Mock()
        cache_size = 4 * 1024
        remain_size = vdi_handler.CHUNK_SIZE / 2
        file_size = cache_size + vdi_handler.CHUNK_SIZE * 2 + remain_size
        image_cmd = vdi_handler.ImageStreamToVDIs(self.context, self.session,
                                                  self.instance, self.host_url,
                                                  self.stream)
        mock_parser = mock.Mock()
        mock_parser.cached_buff = b'\x00' * cache_size
        mock_parser.src_file = vdh_stream
        image_cmd.task_ref = 'fake-task-ref'
        vdh_stream.read.return_value = ['chunk1', 'chunk2', 'chunk3']

        self.assertRaises(exception.VdiImportFailure,
                          image_cmd._vhd_stream_to_vdi, mock_parser,
                          'fake_vdi_ref', file_size)

    @mock.patch.object(utils, 'get_vdi_import_path',
                       return_value='fake-path')
    @mock.patch.object(httplib.HTTPConnection, 'connect',
                       side_effect=Exception)
    @mock.patch.object(httplib.HTTPConnection, 'request')
    @mock.patch.object(httplib.HTTPConnection, 'send')
    @mock.patch.object(httplib.HTTPConnection, 'getresponse')
    @mock.patch.object(httplib.HTTPConnection, 'close')
    def test_vhd_stream_to_vdi_conn_except(self, conn_close, conn_getRes,
                                           conn_send, conn_req, conn_connect,
                                           get_path):
        vdh_stream = mock.Mock()
        cache_size = 4 * 1024
        remain_size = vdi_handler.CHUNK_SIZE / 2
        file_size = cache_size + vdi_handler.CHUNK_SIZE * 2 + remain_size
        image_cmd = vdi_handler.ImageStreamToVDIs(self.context, self.session,
                                                  self.instance, self.host_url,
                                                  self.stream)
        mock_parser = mock.Mock()
        mock_parser.cached_buff = b'\x00' * cache_size
        mock_parser.src_file = vdh_stream
        image_cmd.task_ref = 'fake-task-ref'
        vdh_stream.read.return_value = ['chunk1', 'chunk2', 'chunk3']

        self.assertRaises(exception.HostConnectionFailure,
                          image_cmd._vhd_stream_to_vdi, mock_parser,
                          'fake_vdi_ref', file_size)


class GenerateImageStreamTestCase(base.TestCase):
    def setUp(self):
        super(GenerateImageStreamTestCase, self).setUp()
        self.context = mock.Mock()
        self.session = mock.Mock()
        self.instance = {'name': 'instance-001'}
        self.host_url = "http://fake-host.com"
        self.stream = mock.Mock()

    @mock.patch.object(utils, 'create_pipe')
    @mock.patch.object(eventlet.GreenPool, 'spawn')
    @mock.patch.object(vdi_handler.GenerateImageStream,
                       'start_image_stream_generator')
    @mock.patch.object(eventlet.GreenPool, 'waitall')
    def test_get_image_data(self, mock_waitall, mock_start, mock_spawn,
                            create_pipe):
        mock_tarpipe_out = mock.Mock()
        mock_tarpipe_in = mock.Mock()
        create_pipe.return_value = (mock_tarpipe_out, mock_tarpipe_in)
        image_cmd = vdi_handler.GenerateImageStream(
            self.context, self.session, self.instance,
            self.host_url, ['vdi_uuid'])
        mock_tarpipe_out.read.side_effect = ['chunk1', 'chunk2', '']

        image_chunks = []
        for chunk in image_cmd.get_image_data():
            image_chunks.append(chunk)

        create_pipe.assert_called_once_with()
        mock_spawn.assert_called_once_with(mock_start, mock_tarpipe_in)
        self.assertEqual(image_chunks, ['chunk1', 'chunk2'])


class VdisToTarStreamTestCase(base.TestCase):
    def setUp(self):
        super(VdisToTarStreamTestCase, self).setUp()
        self.context = mock.Mock()
        self.session = mock.Mock()
        self.instance = {'name': 'instance-001'}
        self.host_url = "http://fake-host.com"
        self.stream = mock.Mock()

    @mock.patch.object(tarfile, 'open')
    @mock.patch.object(tarfile, 'TarInfo')
    @mock.patch.object(vdi_handler.VdisToTarStream, '_connect_request',
                       return_value='fake-conn-resp')
    @mock.patch.object(vhd_utils, 'VHDDynDiskParser')
    @mock.patch.object(utils, 'create_pipe')
    @mock.patch.object(vdi_handler.VdisToTarStream, 'convert_vhd_to_tar')
    @mock.patch.object(eventlet.GreenPool, 'spawn')
    @mock.patch.object(vdi_handler.VdisToTarStream, '_vhd_to_pipe')
    @mock.patch.object(eventlet.GreenPool, 'waitall')
    def test_start(self, mock_waitall, mock_to_pipe, mock_spawn,
                   mock_convert, mock_pipe, mock_parser,
                   mock_conn_req, mock_tarinfo, mock_open):
        mock_tarfile = mock.MagicMock()
        mock_tarfile.__enter__.return_value = mock_tarfile
        mock_open.return_value = mock_tarfile
        mock_tarinfo.return_value = mock.sentinel.tar_info
        self.session.VDI.get_by_uuid.return_value = 'fake-vdi-ref'
        mock_dynDisk = mock.Mock()
        mock_parser.return_value = mock_dynDisk
        mock_dynDisk.get_vhd_file_size.return_value = 29371904
        vdi_uuids = ['vdi-uuid']
        vhdpipe_in = mock.Mock()
        mock_pipe.return_value = ('vhdpipe_out', vhdpipe_in)
        image_cmd = vdi_handler.VdisToTarStream(
            self.context, self.session, self.instance,
            self.host_url, vdi_uuids, self.stream)

        image_cmd.start()

        mock_open.assert_called_once_with(fileobj=self.stream,
                                          mode='w|gz')
        self.session.VDI.get_by_uuid.assert_called_once_with('vdi-uuid')
        mock_conn_req.assert_called_once_with('fake-vdi-ref')
        mock_dynDisk.get_vhd_file_size.assert_called_once_with()
        mock_pipe.assert_called_once_with()
        mock_spawn.assert_called_once_with(mock_convert, 'vhdpipe_out',
                                           mock_tarfile,
                                           mock.sentinel.tar_info)
        mock_to_pipe.assert_called_once_with(mock_dynDisk, vhdpipe_in)
        vhdpipe_in.close.asset_called_once_with()
        mock_waitall.assert_called_once_with()


class AddVhdToTarTestCase(base.TestCase):
    def setUp(self):
        super(AddVhdToTarTestCase, self).setUp()
        self.context = mock.Mock()
        self.session = mock.Mock()
        self.instance = {'name': 'instance-001'}
        self.host_url = "http://fake-host.com"
        self.stream = mock.Mock()

    def test_add_stream_to_tar(self):
        mock_tar_file = mock.Mock()
        mock_tar_info = mock.Mock()
        mock_tar_info.size = 8196
        mock_tar_info.name = '0.vhd'
        image_cmd = vdi_handler.AddVhdToTar(mock_tar_file, mock_tar_info,
                                            'fake-vhdpipe-out')

        image_cmd.start()

        mock_tar_file.addfile.assert_called_once_with(
            mock_tar_info, fileobj='fake-vhdpipe-out')

    def test_add_stream_to_tar_IOError(self):
        mock_tar_file = mock.Mock()
        mock_tar_info = mock.Mock()
        mock_tar_info.size = 1024
        mock_tar_info.name = '0.vhd'
        image_cmd = vdi_handler.AddVhdToTar(mock_tar_file, mock_tar_info,
                                            'fake-vhdpipe-out')
        mock_tar_file.addfile.side_effect = IOError

        self.assertRaises(IOError, image_cmd.start)
