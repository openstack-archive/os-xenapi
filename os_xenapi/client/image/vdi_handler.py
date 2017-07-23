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

import eventlet
from eventlet import greenio
import logging
import os
from six.moves import http_client as httplib
import six.moves.urllib.parse as urlparse
import struct
import tarfile

from os_xenapi.client import exception
from os_xenapi.client import utils

LOG = logging.getLogger(__name__)


CHUNK_SIZE = 16 * 1024


class ImageCommand(object):
    def start(self):
        raise NotImplementedError()

    def create_pipe(self):
        rpipe, wpipe = os.pipe()
        rfile = greenio.GreenPipe(rpipe, 'rb', 0)
        wfile = greenio.GreenPipe(wpipe, 'wb', 0)
        return rfile, wfile

    def create_task(self, session, label, desc=''):
        task_ref = session.call_xenapi("task.create", label, desc)
        return task_ref

    def destroy_task(self, session, task_ref):
        LOG.debug('destroy_task %s' % task_ref)
        session.call_xenapi("task.destroy", task_ref)

    def close_stream(self, stream):
        if not stream.closed:
            stream.close()

    def get_vdi_import_path(self, session, task_ref, vdi_ref):
        session_id = session.get_session_id()
        str_fmt = '/import_raw_vdi?session_id={}&task_id={}&vdi={}&format=vhd'
        return str_fmt.format(session_id, task_ref, vdi_ref)

    def get_vdi_export_path(self, session, task_ref, vdi_ref):
        session_id = session.get_session_id()
        str_fmt = '/export_raw_vdi?session_id={}&task_id={}&vdi={}&format=vhd'
        return str_fmt.format(session_id, task_ref, vdi_ref)


class ImageStreamToVDIs(ImageCommand):
    def __init__(self, context, session, instance, host_url, stream):
        self.context = context
        self.session = session
        self.instance = instance
        self.host_url = urlparse.urlparse(host_url)
        self.stream = stream
        self.task_ref = None
        self.cache = ''
        self.vdis = {}

    def _clean(self):
        if self.task_ref:
            self.destroy_task(self.session, self.task_ref)

    def start(self):
        task_name_label = 'VDI_IMPORT_for_' + self.instance['name']
        self.task_ref = self.create_task(self.session, task_name_label)
        with tarfile.open(mode="r|gz", fileobj=self.stream) as tar:
            for vhd in tar:
                file_size = vhd.size
                LOG.debug("file_name:file_size is %(n)s:%(s)d",
                          {'n': vhd.name, 's': vhd.size})
                file_obj = tar.extractfile(vhd)
                virtual_size = self._get_virtual_size(file_obj)
                sr_ref, vdi_ref = self._createVDI(self.session, self.instance,
                                                  virtual_size)

                self._vhd_stream_to_vdi(vdi_ref, file_obj, file_size)
                vdi_uuid = self.session.call_xenapi('VDI.get_uuid', vdi_ref)
                if vhd.name == '0.vhd':
                    self.vdis['root'] = dict(uuid=vdi_uuid)
                else:
                    self.vdis[vhd.name] = dict(uuid=vdi_uuid)
        self._clean()

    def _get_virtual_size(self, fileobj):
        HEADER_SIZE = 512
        self.cache = fileobj.read(HEADER_SIZE)
        fmt = '!Q'
        (virtual_size, ) = struct.unpack(fmt, self.cache[48:56])
        return virtual_size

    def _createVDI(self, session, instance, virtual_size):
        sr_ref = utils.get_default_sr(session)
        vdi_ref = utils.create_vdi(session, sr_ref, instance,
                                   instance['name'], 'root', virtual_size)
        LOG.debug("vdi_ref is %s" % vdi_ref)
        return sr_ref, vdi_ref

    def _vhd_stream_to_vdi(self, vdi_ref, file_obj, file_size):
        headers = {'Content-Type': 'application/octet-stream',
                   'Content-Length': '%s' % file_size}

        if self.host_url.scheme == 'http':
            conn = httplib.HTTPConnection(self.host_url.netloc)
        elif self.host_url.scheme == 'https':
            conn = httplib.HTTPSConnection(self.host_url.netloc)

        vdi_import_path = self.get_vdi_import_path(
            self.session, self.task_ref, vdi_ref)
        try:
            conn.connect()
        except Exception:
            LOG.error('Failed connecting to host: %s', self.host_url.netloc)
            raise exception.HostConnectionFailure(
                host_netloc=self.host_url.netloc)

        try:
            conn.request('PUT', vdi_import_path, headers=headers)
            # replay the cached content
            conn.send(self.cache)
            remain_size = file_size - len(self.cache)
            while remain_size >= CHUNK_SIZE:
                trunk = file_obj.read(CHUNK_SIZE)
                remain_size -= CHUNK_SIZE
                conn.send(trunk)
            if remain_size != 0:
                trunk = file_obj.read(remain_size)
                conn.send(trunk)
        except Exception:
            LOG.error('Failed importing VDI from VHD stream - vdi_ref:%s',
                      vdi_ref)
            raise exception.VdiImportFailure(vdi_ref=vdi_ref)
        finally:
            resp = conn.getresponse()
            LOG.debug("the connection response status:reason is "
                      "%(status)s:%(reason)s",
                      {'status': resp.status, 'reason': resp.reason})
            conn.close()


class GenerateImageStream(ImageCommand):
    def __init__(self, context, session, instance, host_url, vdi_uuids):
        self.context = context
        self.session = session
        self.instance = instance
        self.host_url = host_url
        self.vdi_uuids = vdi_uuids

    def get_image_data(self):
        """This function will:

          1). export VDI as VHD stream;
          2). make gzipped tarball from the VHD stream;
          3). read from the tarball stream.and return the iterable data.
        """

        tarfile_r, tarfile_w = self.create_pipe()
        stream_generator = VdisToTarStream(
            self.context, self.session, self.instance, self.host_url,
            self.vdi_uuids, tarfile_w)
        pool = eventlet.GreenPool()
        pool.spawn(stream_generator.start)
        while True:
            try:
                data = tarfile_r.read(CHUNK_SIZE)
                if not data:
                    break
                yield data
            except Exception:
                LOG.debug("Failed to read chunks from the tarfile"
                          "stream.")
                raise
        pool.waitall()


class VdisToTarStream(ImageCommand):
    def __init__(self, context, session, instance, host_url, vdi_uuids,
                 stream):
        self.context = context
        self.session = session
        self.instance = instance
        self.host_url = host_url
        self.vdi_uuids = vdi_uuids
        self.stream = stream
        self.conn = None
        self.task_ref = None
        self.cache = b''

    def start(self):
        with tarfile.open(fileobj=self.stream, mode='w|gz') as tar_file:
            vdi_uuid = self.vdi_uuids[0]
            vdi_ref = self.session.call_xenapi("VDI.get_by_uuid", vdi_uuid)
            conn_resp = self._connect_request(vdi_ref)
            tar_info = tarfile.TarInfo('0.vhd')
            tar_info.size = self.get_vhd_size(conn_resp)
            LOG.debug("tar_info.size is %d" % tar_info.size)
            readfile, writefile = self.create_pipe()
            consumer = AddStreamToTar(tar_file, tar_info, readfile)
            pool = eventlet.GreenPool()
            pool.spawn(consumer.start)
            self._vhd_to_stream(conn_resp, writefile)
            pool.waitall()

    def _connect_request(self, vdi_ref):
        # request connection to xapi url service for VDI export
        try:
            # create task for VDI export
            task_name_label = 'VDI_EXPORT_for_' + self.instance['name']
            self.task_ref = self.create_task(self.session, task_name_label)
            LOG.debug("task_ref is %s" % self.task_ref)
            # connect to XS
            xs_url = urlparse.urlparse(self.host_url)
            if xs_url.scheme == 'http':
                conn = httplib.HTTPConnection(xs_url.netloc)
                LOG.debug("using http")
            elif xs_url.scheme == 'https':
                conn = httplib.HTTPSConnection(xs_url.netloc)
                LOG.debug("using https")
            vdi_svc_path = self.get_vdi_export_path(
                self.session, self.task_ref, vdi_ref)
            conn.request('GET', vdi_svc_path)
            conn_resp = conn.getresponse()
        except Exception:
            LOG.debug('request connect for vdi export failed')
            raise
        return conn_resp

    def _vhd_to_stream(self, conn_resp, stream):
        # replay the cached content
        stream.write(self.cache)
        while True:
            data = conn_resp.read(CHUNK_SIZE)
            if not data:
                break
            try:
                stream.write(data)
            except Exception:
                LOG.debug("Failed when writing data to VHD stream.")
                raise
        stream.flush()
        stream.close()

    def get_vhd_size(self, conn_resp):
        """Calculate size for the VHD file which is streaming from conn_resp.

        The exported VHD should be a "Dynamic Hard Disk Image" and all of
        the data blocks should be continuously placed in the VHD file.
        https://www.microsoft.com/en-us/download/confirmation.aspx?id=23850
        "Virtual Hard Disk Image Format Specification"
        The Dynamic Hard Disk Image format is as below:
         +-----------------------------------------------+
         |Mirror Image of Hard drive footer (512 bytes)  |
         +-----------------------------------------------+
         |Dynamic Disk Header (1024 bytes)               |
         +-----------------------------------------------+
         | padding bytes                                 |
         |(Table Offset in Dynamic Disk Header determines|
         | where the BAT starts from)                    |
         +-----------------------------------------------+
         |BAT (Block Allocation Table)                   |
         |(BAT entries + padding byte to make BAT to a   |
         | 512-byte sector boundary)                     |
         +-----------------------------------------------+
         | bitmap 1 (512 bytes)                          |
         | Data Block 1                                  |
         +-----------------------------------------------+
         | bitmap 2 (512 bytes)                          |
         | Data Block 2                                  |
         +-----------------------------------------------+
         | ...                                           |
         +-----------------------------------------------+
         | bitmap 1 (512 bytes)                          |
         | Data Block n                                  |
         +-----------------------------------------------+
         | Hard drive footer (512 bytes)                 |
         +-----------------------------------------------+
         The Dynamic Disk Header(DDH) layout is as below:
            |**fields**             | **size**|
            |Cookie                 |    8    |
            |Data Offset            |    8    |
            |*Table Offset*         |    8    |
            |Header Version         |    4    |
            |*Max Table Entries*    |    4    |
            |*Block Size*           |    4    |
            |Checksum               |    4    |
            |Parent Unique ID       |    16   |
            |Parent Time Stamp      |    4    |
            |Reserved               |    4    |
            |Parent Unicode Name    |    512  |
            |Parent Locator Entry 1 |    24   |
            |Parent Locator Entry 2 |    24   |
            |Parent Locator Entry 3 |    24   |
            |Parent Locator Entry 4 |    24   |
            |Parent Locator Entry 5 |    24   |
            |Parent Locator Entry 6 |    24   |
            |Parent Locator Entry 7 |    24   |
            |Parent Locator Entry 8 |    24   |
            |Reserved               |    256  |

         file_size = DDH_BAT_OFFSET + SIZE_OF_BAT_PADDED +
          (SIZE_PER_BITMAP + DDH_SIZE_PER_BLOCK) * NUM_OF_VALID_BAT_ENT
           + SIZE_OF_FOOTER
        """

        FMT_TO_LEN = {
            '!B': 1,
            '!H': 2,
            '!I': 4,
            '!Q': 8,
        }
        FMT_BAT_ENT = '!I'
        SIZE_OF_BITMAP = 512
        SIZE_OF_FOOTER = 512
        SIZE_OF_DDH = 1024
        START_OF_DDH = SIZE_OF_FOOTER
        # Define the data fields' format and their internal offset in the DDH
        # (Dynamic Disk Header).
        FMT_DDH_BAT_OFFSET = '!Q'
        OFFSET_DDH_BAT_OFFSET = 16
        FMT_DDH_MAX_BAT_ENTRIES = '!I'
        OFFSET_DDH_MAX_BAT_ENTRIES = 28
        FMT_DDH_BLOCK_SIZE = '!I'
        OFFSET_DDH_BLOCK_SIZE = 32

        # Read in the footer and DDH and parse the data to get needed fields.
        buf = conn_resp.read(SIZE_OF_FOOTER + SIZE_OF_DDH)
        self.cache += buf

        # get the offset for BAT
        start = START_OF_DDH + OFFSET_DDH_BAT_OFFSET
        end = start + FMT_TO_LEN[FMT_DDH_BAT_OFFSET]
        (bat_offset, ) = struct.unpack(FMT_DDH_BAT_OFFSET,
                                       buf[start: end])
        # get the MAX number of BAT entries.
        start = START_OF_DDH + OFFSET_DDH_MAX_BAT_ENTRIES
        end = start + FMT_TO_LEN[FMT_DDH_MAX_BAT_ENTRIES]
        (max_bat_entry_num, ) = struct.unpack(FMT_DDH_MAX_BAT_ENTRIES,
                                              buf[start: end])
        # get the data block size.
        start = START_OF_DDH + OFFSET_DDH_BLOCK_SIZE
        end = start + FMT_TO_LEN[FMT_DDH_BLOCK_SIZE]
        (size_of_block, ) = struct.unpack(FMT_DDH_BLOCK_SIZE,
                                          buf[start: end])

        # read in BAT entries.
        size_of_bat = FMT_TO_LEN[FMT_BAT_ENT] * max_bat_entry_num
        size_to_read = bat_offset + size_of_bat - len(self.cache)
        buf = conn_resp.read(size_to_read)
        self.cache += buf

        # Calculate number of the valid BAT entries.
        # We will go through all BAT entries, it will be treated as valid BAT
        # entry if value if it's not the default one - 0xFFFFFFFF..
        num_of_valid_bat_ent = 0
        size_of_bat_entry = FMT_TO_LEN[FMT_BAT_ENT]
        for i in range(bat_offset, len(self.cache), size_of_bat_entry):
            (value, ) = struct.unpack(FMT_BAT_ENT,
                                      self.cache[i: i + size_of_bat_entry])
            if value != 0xFFFFFFFF:
                num_of_valid_bat_ent += 1

        if size_of_bat % 512 != 0:
            # padding to 512 sector boundary
            size_of_bat = (size_of_bat / 512 + 1) * 512

        # the size of bitmaps and data blocks
        size_of_data = (SIZE_OF_BITMAP + size_of_block) * num_of_valid_bat_ent

        size_of_vhd = bat_offset + size_of_bat + size_of_data + SIZE_OF_FOOTER
        LOG.debug("Caculated vhd_size = %d" % size_of_vhd)
        return size_of_vhd

    def clean(self):
        self.close_stream(self.stream)
        if self.conn:
            self.conn.close()
        if self.task_ref:
            self.destroy_task(self.session, self.task_ref)


class AddStreamToTar(ImageCommand):
    def __init__(self, tar_file, tar_info, stream):
        self.tar_file = tar_file
        self.tar_info = tar_info
        self.stream = stream

    def start(self):
        self._add_stream_to_tar()

    def _add_stream_to_tar(self):
        try:
            LOG.debug('self.tar_info.size=%d' % self.tar_info.size)
            self.tar_file.addfile(self.tar_info, fileobj=self.stream)
            LOG.debug('added file %s' % self.tar_info.name)
        except IOError:
            LOG.debug('IOError when streaming vhd to tarball')
            raise
        finally:
            self.close_stream(self.stream)


def stream_to_vdis(context, session, instance, host_url, data):
    handler = ImageStreamToVDIs(context, session, instance, host_url, data)
    handler.start()
    return handler.vdis


def vdis_to_stream(context, session, instance, host_url, vdi_uuids):
    handler = GenerateImageStream(context, session, instance, host_url,
                                  vdi_uuids)
    return handler.get_image_data()
