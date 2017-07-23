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
import struct
import tarfile


from os_xenapi.client import exception
from os_xenapi.client.image import vdi_handler
from os_xenapi.client import utils
from os_xenapi.tests import base


class ImageCommandTestCase(base.TestCase):
    def setUp(self):
        super(ImageCommandTestCase, self).setUp()
        self.session = mock.Mock()

    def test_create_task(self):
        image_command = vdi_handler.ImageCommand()
        image_command.create_task(self.session, 'fake-label', 'fake-desc')

        self.session.call_xenapi.assert_called_once_with(
            "task.create", 'fake-label', 'fake-desc')

    def test_destroy_task(self):
        image_command = vdi_handler.ImageCommand()
        image_command.destroy_task(self.session, 'fake-task-ref')

        self.session.call_xenapi.assert_called_once_with(
            "task.destroy", 'fake-task-ref')

    def test_close_opened_stream(self):
        stream = mock.Mock()
        stream.closed = False

        image_command = vdi_handler.ImageCommand()
        image_command.close_stream(stream)

        stream.close.assert_called_once_with()

    def test_close_closed_stream(self):
        stream = mock.Mock()
        stream.closed = True

        image_command = vdi_handler.ImageCommand()
        image_command.close_stream(stream)

        stream.close.assert_not_called()

    def test_get_vdi_import_path(self):
        self.session.get_session_id.return_value = 'fake_sid'
        expected_path = '/import_raw_vdi?session_id=fake_sid' + \
                        '&task_id=fake-task-ref&vdi=fake_vid_ref' + \
                        '&format=vhd'

        image_command = vdi_handler.ImageCommand()
        path = image_command.get_vdi_import_path(self.session, 'fake-task-ref',
                                                 'fake_vid_ref')

        self.assertEqual(expected_path, path)

    def test_get_vdi_export_path(self):
        self.session.get_session_id.return_value = 'fake_sid'
        expected_path = '/export_raw_vdi?session_id=fake_sid' + \
                        '&task_id=fake-task-ref&vdi=fake_vid_ref' + \
                        '&format=vhd'

        image_command = vdi_handler.ImageCommand()
        path = image_command.get_vdi_export_path(self.session, 'fake-task-ref',
                                                 'fake_vid_ref')

        self.assertEqual(expected_path, path)


class ImageStreamToVDIsTestCase(base.TestCase):
    def setUp(self):
        super(ImageStreamToVDIsTestCase, self).setUp()
        self.context = mock.Mock()
        self.session = mock.Mock()
        self.instance = {'name': 'instance-001'}
        self.host_url = "http://fake-host.com"
        self.stream = mock.Mock()

    @mock.patch.object(vdi_handler.ImageCommand, 'create_task',
                       return_value='fake-task-ref')
    @mock.patch.object(tarfile, 'open')
    @mock.patch.object(vdi_handler.ImageStreamToVDIs, '_get_virtual_size',
                       return_value=1073741824)
    @mock.patch.object(vdi_handler.ImageStreamToVDIs, '_createVDI',
                       return_value=('fake_sr_ref', 'fake_vdi_ref'))
    @mock.patch.object(vdi_handler.ImageStreamToVDIs, '_vhd_stream_to_vdi')
    @mock.patch.object(vdi_handler.ImageStreamToVDIs, '_clean')
    def test_start(self, mock_clean, mock_to_vdi, mock_createVDI,
                   mock_get_vsize, mock_open, mock_create_task):
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

        mock_create_task.assert_called_once_with(self.session,
                                                 'VDI_IMPORT_for_instance-001')
        mock_open.assert_called_once_with(mode="r|gz", fileobj=self.stream)
        mock_tarfile.extractfile.assert_called_once_with(fake_vhd_info)
        mock_createVDI.assert_called_once_with(self.session, self.instance,
                                               1073741824)
        mock_to_vdi.assert_called_once_with('fake_vdi_ref', 'fake-file-obj',
                                            29371904)
        self.session.call_xenapi.assert_called_once_with('VDI.get_uuid',
                                                         'fake_vdi_ref')
        mock_clean.assert_called_once_with()

    def test_get_virtual_size(self):
        mock_fileobj = mock.Mock()
        ONE_GB = 1 * 1024 * 1024 * 1024
        header_data = b'\x00' * 48 + struct.pack('!Q', ONE_GB)
        mock_fileobj.read.return_value = header_data

        image_cmd = vdi_handler.ImageStreamToVDIs(self.context, self.session,
                                                  self.instance, self.host_url,
                                                  self.stream)
        size = image_cmd._get_virtual_size(mock_fileobj)

        mock_fileobj.read.assert_called_once_with(512)
        self.assertEqual(size, ONE_GB)

    @mock.patch.object(utils, 'get_default_sr',
                       return_value='fake-sr-ref')
    @mock.patch.object(utils, 'create_vdi',
                       return_value='fake-vdi-ref')
    def test_createVDI(self, mock_create_vdi, mock_get_sr):
        virtual_size = 1073741824
        image_cmd = vdi_handler.ImageStreamToVDIs(self.context, self.session,
                                                  self.instance, self.host_url,
                                                  self.stream)

        image_cmd._createVDI(self.session, self.instance, virtual_size)

        mock_get_sr.assert_called_once_with(self.session)
        mock_create_vdi.assert_called_once_with(self.session, 'fake-sr-ref',
                                                self.instance, 'instance-001',
                                                'root', virtual_size)

    @mock.patch.object(vdi_handler.ImageCommand, 'get_vdi_import_path',
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
        image_cmd.cache = b'\x00' * cache_size
        image_cmd.task_ref = 'fake-task-ref'
        vdh_stream.read.side_effect = ['chunk1', 'chunk2', 'chunk3']

        image_cmd._vhd_stream_to_vdi('fake_vdi_ref', vdh_stream, file_size)

        conn_connect.assert_called_once_with()
        get_path.assert_called_once_with(self.session, 'fake-task-ref',
                                         'fake_vdi_ref')
        conn_connect.assert_called_once_with()
        conn_req.assert_called_once_with('PUT', 'fake-path', headers=headers)
        expect_send_calls = [mock.call(image_cmd.cache),
                             mock.call('chunk1'),
                             mock.call('chunk2'),
                             mock.call('chunk3'),
                             ]
        conn_send.assert_has_calls(expect_send_calls)
        conn_getRes.assert_called_once_with()
        conn_close.assert_called_once_with()

    @mock.patch.object(vdi_handler.ImageCommand, 'get_vdi_import_path',
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
        image_cmd.cache = b'\x00' * cache_size
        image_cmd.task_ref = 'fake-task-ref'
        vdh_stream.return_value = ['chunk1', 'chunk2', 'chunk3']

        self.assertRaises(exception.VdiImportFailure,
                          image_cmd._vhd_stream_to_vdi, 'fake_vdi_ref',
                          vdh_stream, file_size)

    @mock.patch.object(vdi_handler.ImageCommand, 'get_vdi_import_path',
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
        image_cmd.cache = b'\x00' * cache_size
        image_cmd.task_ref = 'fake-task-ref'
        vdh_stream.return_value = ['chunk1', 'chunk2', 'chunk3']

        self.assertRaises(exception.HostConnectionFailure,
                          image_cmd._vhd_stream_to_vdi, 'fake_vdi_ref',
                          vdh_stream, file_size)


class GenerateImageStreamTestCase(base.TestCase):
    def setUp(self):
        super(GenerateImageStreamTestCase, self).setUp()
        self.context = mock.Mock()
        self.session = mock.Mock()
        self.instance = {'name': 'instance-001'}
        self.host_url = "http://fake-host.com"
        self.stream = mock.Mock()

    @mock.patch.object(vdi_handler.ImageCommand, 'create_pipe')
    @mock.patch.object(eventlet.GreenPool, 'spawn')
    @mock.patch.object(vdi_handler.VdisToTarStream, 'start')
    @mock.patch.object(eventlet.GreenPool, 'waitall')
    def test_get_image_data(self, mock_waitall, mock_start, mock_spawn,
                            create_pipe):
        mock_tarfile_r = mock.Mock()
        mock_tarfile_w = mock.Mock()
        create_pipe.return_value = (mock_tarfile_r, mock_tarfile_w)
        image_cmd = vdi_handler.GenerateImageStream(
            self.context, self.session, self.instance,
            self.host_url, self.stream)
        mock_tarfile_r.read.side_effect = ['chunk1', 'chunk2', '']

        image_chunks = []
        for chunk in image_cmd.get_image_data():
            image_chunks.append(chunk)

        create_pipe.assert_called_once_with()
        mock_spawn.assert_called_once_with(mock_start)
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
    @mock.patch.object(vdi_handler.VdisToTarStream, '_connect_request',
                       return_value='fake-conn-resp')
    @mock.patch.object(vdi_handler.VdisToTarStream, 'get_vhd_size')
    @mock.patch.object(vdi_handler.ImageCommand, 'create_pipe')
    @mock.patch.object(vdi_handler.AddStreamToTar, 'start')
    @mock.patch.object(eventlet.GreenPool, 'spawn')
    @mock.patch.object(vdi_handler.VdisToTarStream, '_vhd_to_stream')
    @mock.patch.object(eventlet.GreenPool, 'waitall')
    def test_start(self, mock_waitall, mock_to_stream, mock_spawn,
                   mock_start, mock_pipe, mock_get_size,
                   mock_conn_req, mock_open):
        self.session.call_xenapi.return_value = 'fake-vdi-ref'
        vid_uuids = ['vid-uuid']
        mock_pipe.return_value = ('readfile', 'writefile')
        image_cmd = vdi_handler.VdisToTarStream(
            self.context, self.session, self.instance,
            self.host_url, vid_uuids, self.stream)

        image_cmd.start()

        mock_open.assert_called_once_with(fileobj=self.stream,
                                          mode='w|gz')
        self.session.call_xenapi.assert_called_once_with("VDI.get_by_uuid",
                                                         'vid-uuid')
        mock_conn_req.assert_called_once_with('fake-vdi-ref')
        mock_get_size.assert_called_once_with('fake-conn-resp')
        mock_pipe.assert_called_once_with()
        mock_spawn.assert_called_once_with(mock_start)
        mock_to_stream.assert_called_once_with('fake-conn-resp', 'writefile')
        mock_waitall.assert_called_once_with()

    def test_get_vhd_size(self):
        conn_resp = mock.Mock()
        SIZE_OF_FOOTER = 512
        SIZE_OF_DDH = 1024
        SIZE_PADDING = 512
        MAX_BAT_ENTRIES = 512
        SIZE_OF_BAT_ENTRY = 4
        SIZE_OF_BITMAP = 512
        SIZE_OF_DATA_BLOCK = 2 * 1024 * 1024
        # Construct the DDH(Dynamical Disk Header) fields.
        DDH_BAT_OFFSET = struct.pack('!Q', 2048)
        DDH_MAX_BAT_ENTRIES = struct.pack('!I', MAX_BAT_ENTRIES)
        DDH_BLOCK_SIZE = struct.pack('!I', SIZE_OF_DATA_BLOCK)
        DATA_FOOTER_AND_DDH = b'\x00' * SIZE_OF_FOOTER
        DATA_FOOTER_AND_DDH += b'\x00' * 16 + DDH_BAT_OFFSET + \
                               b'\x00' * 4 + DDH_MAX_BAT_ENTRIES + \
                               DDH_BLOCK_SIZE
        DATA_FOOTER_AND_DDH += b'\x00' * (SIZE_OF_DDH - 36)

        # Construct the padding bytes
        DATA_PADDING = b'\x00' * SIZE_PADDING
        # Construct BAT(Block Allocation Table)
        # The non 0xffffffff means a valid BAT entry. Let's give some holes.
        # At here the DATA_BAT contains 14 valid entries in the first 16
        # 4-bytes units; there are 2 holes - 0xffffffff which should be
        # ignored.
        DATA_BAT = b'\x00\x00\x00\x08\x00\x00\x50\x0d\xff\xff\xff\xff' + \
                   b'\x00\x00\x10\x09\x00\x00\x20\x0a\x00\x00\x30\x0b' + \
                   b'\x00\x00\x40\x0c\xff\xff\xff\xff\x00\x00\x60\x0e' + \
                   b'\x00\x00\x70\x0f\x00\x00\x80\x10\x00\x00\x90\x11' + \
                   b'\x00\x00\xa0\x12\x00\x00\xb0\x13\x00\x00\xc0\x14' + \
                   b'\x00\x00\xd0\x15' + \
                   b'\xff\xff\xff\xff' * (MAX_BAT_ENTRIES - 16)
        expected_size = SIZE_OF_FOOTER * 2 + SIZE_OF_DDH
        expected_size += SIZE_PADDING + SIZE_OF_BAT_ENTRY * MAX_BAT_ENTRIES
        expected_size += (SIZE_OF_BITMAP + SIZE_OF_DATA_BLOCK) * 14

        conn_resp.read.side_effect = [DATA_FOOTER_AND_DDH,
                                      DATA_PADDING + DATA_BAT]

        image_cmd = vdi_handler.VdisToTarStream(
            self.context, self.session, self.instance,
            self.host_url, 'vid_uuids', self.stream)
        vhd_size = image_cmd.get_vhd_size(conn_resp)

        read_call_list = conn_resp.read.call_args_list
        read_size_1 = SIZE_OF_FOOTER + SIZE_OF_DDH
        read_size_2 = SIZE_PADDING + SIZE_OF_BAT_ENTRY * MAX_BAT_ENTRIES
        expected = [mock.call(read_size_1),
                    mock.call(read_size_2)
                    ]
        self.assertEqual(expected, read_call_list)
        self.assertEqual(expected_size, vhd_size)


class AddStreamToTarTestCase(base.TestCase):
    def setUp(self):
        super(AddStreamToTarTestCase, self).setUp()
        self.context = mock.Mock()
        self.session = mock.Mock()
        self.instance = {'name': 'instance-001'}
        self.host_url = "http://fake-host.com"
        self.stream = mock.Mock()

    @mock.patch.object(vdi_handler.ImageCommand, 'close_stream')
    def test_add_stream_to_tar(self, mock_close):
        mock_tar_file = mock.Mock()
        mock_tar_info = mock.Mock()
        mock_tar_info.size = 8196
        mock_tar_info.name = '0.vhd'
        image_cmd = vdi_handler.AddStreamToTar(mock_tar_file, mock_tar_info,
                                               'fake-stream')

        image_cmd.start()

        mock_tar_file.addfile.assert_called_once_with(mock_tar_info,
                                                      fileobj='fake-stream')
        mock_close.assert_called_once_with('fake-stream')

    @mock.patch.object(vdi_handler.ImageCommand, 'close_stream')
    def test_add_stream_to_tar_IOError(self, mock_close):
        mock_tar_file = mock.Mock()
        mock_tar_info = mock.Mock()
        mock_tar_info.size = 1024
        mock_tar_info.name = '0.vhd'
        image_cmd = vdi_handler.AddStreamToTar(mock_tar_file, mock_tar_info,
                                               'fake-stream')
        mock_tar_file.addfile.side_effect = IOError

        self.assertRaises(IOError, image_cmd.start)


class VdiStreamTestCase(base.TestCase):
    def setUp(self):
        super(VdiStreamTestCase, self).setUp()
        self.context = mock.Mock()
        self.session = mock.Mock()
        self.instance = {'name': 'instance-001'}
        self.host_url = "http://fake-host.com"
        self.stream = mock.Mock()

    @mock.patch.object(vdi_handler.ImageStreamToVDIs, 'start')
    def test_stream_to_vdis(self, mock_start):
        vdi_handler.stream_to_vdis(self.context, self.session, self.instance,
                                   self.host_url, self.stream)

        mock_start.assert_called_once_with()

    @mock.patch.object(vdi_handler.GenerateImageStream, 'get_image_data')
    def test_vdis_to_stream(self, mock_get):
        vdi_handler.vdis_to_stream(self.context, self.session, self.instance,
                                   self.host_url, 'fake-uuids')

        mock_get.assert_called_once_with()
