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
import logging
from six.moves import http_client as httplib
import six.moves.urllib.parse as urlparse
import tarfile

from os_xenapi.client import exception
from os_xenapi.client.image import vhd_utils
from os_xenapi.client import utils

LOG = logging.getLogger(__name__)


CHUNK_SIZE = 4 * 1024 * 1024


class ImageStreamToVDIs(object):
    def __init__(self, context, session, instance, host_url, image_stream_in):
        self.context = context
        self.session = session
        self.instance = instance
        self.host_url = urlparse.urlparse(host_url)
        self.image_stream = image_stream_in
        self.task_ref = None
        self.vdis = {}

    def _clean(self):
        if self.task_ref:
            self.session.task.destroy(self.task_ref)

    def start(self):
        label = 'VDI_IMPORT_for_' + self.instance['name']
        desc = 'Importing VDI for instance: %s' % self.instance['name']
        self.task_ref = self.session.task.create(label, desc)
        try:
            with tarfile.open(mode="r|gz", fileobj=self.image_stream) as tar:
                for vhd in tar:
                    file_size = vhd.size
                    LOG.debug("file_name:file_size is %(n)s:%(s)d",
                              {'n': vhd.name, 's': vhd.size})
                    vhd_file = tar.extractfile(vhd)
                    vhd_file_parser = vhd_utils.VHDFileParser(vhd_file)
                    vhd_footer = vhd_file_parser.parse_vhd_footer()
                    virtual_size = vhd_footer.current_size
                    sr_ref, vdi_ref = self._createVDI(self.session,
                                                      self.instance,
                                                      virtual_size)

                    self._vhd_stream_to_vdi(vhd_file_parser, vdi_ref,
                                            file_size)
                    vdi_uuid = self.session.VDI.get_uuid(vdi_ref)
                    if 'root' in self.vdis.keys():
                        # we only support single vdi. If 'root' already exists
                        # in the dict, should raise exception.
                        msg = "Only support single VDI; but there are " + \
                              "multiple VDIs in the image."
                        raise exception.InvalidImage(details=msg)

                    self.vdis['root'] = dict(uuid=vdi_uuid)
        finally:
            self._clean()

    def _createVDI(self, session, instance, virtual_size):
        sr_ref = utils.get_default_sr(session)
        vdi_ref = utils.create_vdi(session, sr_ref, instance,
                                   instance['name'], 'root', virtual_size)
        vdi_uuid = session.VDI.get_uuid(vdi_ref)
        LOG.debug("Created a new VDI: uuid=%s" % vdi_uuid)
        return sr_ref, vdi_ref

    def _vhd_stream_to_vdi(self, vhd_file_parser, vdi_ref, file_size):

        headers = {'Content-Type': 'application/octet-stream',
                   'Content-Length': '%s' % file_size}

        if self.host_url.scheme == 'http':
            conn = httplib.HTTPConnection(self.host_url.netloc)
        elif self.host_url.scheme == 'https':
            conn = httplib.HTTPSConnection(self.host_url.netloc)

        vdi_import_path = utils.get_vdi_import_path(
            self.session, self.task_ref, vdi_ref)
        try:
            conn.connect()
        except Exception:
            LOG.error('Failed connecting to host: %s', self.host_url.netloc)
            raise exception.HostConnectionFailure(
                host_netloc=self.host_url.netloc)

        try:
            conn.request('PUT', vdi_import_path, headers=headers)
            # Send the data already processed by vhd file parser firstly;
            # then send the remaining data from the stream.
            conn.send(vhd_file_parser.cached_buff)
            remain_size = file_size - len(vhd_file_parser.cached_buff)
            file_obj = vhd_file_parser.src_file
            while remain_size >= CHUNK_SIZE:
                chunk = file_obj.read(CHUNK_SIZE)
                remain_size -= CHUNK_SIZE
                conn.send(chunk)
            if remain_size != 0:
                chunk = file_obj.read(remain_size)
                conn.send(chunk)
        except Exception:
            LOG.error('Failed importing VDI from VHD stream - vdi_ref:%s',
                      vdi_ref)
            raise exception.VdiImportFailure(vdi_ref=vdi_ref)
        finally:
            resp = conn.getresponse()
            LOG.debug("Connection response status/reason is "
                      "%(status)s:%(reason)s",
                      {'status': resp.status, 'reason': resp.reason})
            conn.close()


class GenerateImageStream(object):
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

        tarpipe_out, tarpipe_in = utils.create_pipe()
        pool = eventlet.GreenPool()
        pool.spawn(self.start_image_stream_generator, tarpipe_in)
        try:
            while True:
                data = tarpipe_out.read(CHUNK_SIZE)
                if not data:
                    break
                yield data
        except Exception:
            LOG.debug("Failed to read chunks from the tarfile "
                      "stream.")
            raise
        finally:
            tarpipe_out.close()
        pool.waitall()

    def start_image_stream_generator(self, tarpipe_in):
        tar_generator = VdisToTarStream(
            self.context, self.session, self.instance, self.host_url,
            self.vdi_uuids, tarpipe_in)
        try:
            tar_generator.start()
        finally:
            tarpipe_in.close()


class VdisToTarStream(object):
    def __init__(self, context, session, instance, host_url, vdi_uuids,
                 tarpipe_in):
        self.context = context
        self.session = session
        self.instance = instance
        self.host_url = host_url
        self.vdi_uuids = vdi_uuids
        self.tarpipe_in = tarpipe_in
        self.conn = None
        self.task_ref = None

    def start(self):
        # Start thread to generate tgz and write tgz data into tarpipe_in.
        with tarfile.open(fileobj=self.tarpipe_in, mode='w|gz') as tar_file:
            # only need export the leaf vdi.
            vdi_uuid = self.vdi_uuids[0]
            vdi_ref = self.session.VDI.get_by_uuid(vdi_uuid)
            vhd_stream = self._connect_request(vdi_ref)
            tar_info = tarfile.TarInfo('0.vhd')
            try:
                # the VHD must be dynamical hard disk, otherwise it will raise
                # VhdDiskTypeNotSupported exception when parsing VDH file.
                vhd_DynDisk = vhd_utils.VHDDynDiskParser(vhd_stream)
                tar_info.size = vhd_DynDisk.get_vhd_file_size()
                LOG.debug("VHD size for tarfile is %d" % tar_info.size)
                vhdpipe_out, vhdpipe_in = utils.create_pipe()
                pool = eventlet.GreenPool()
                pool.spawn(self.convert_vhd_to_tar, vhdpipe_out,
                           tar_file, tar_info)
                try:
                    self._vhd_to_pipe(vhd_DynDisk, vhdpipe_in)
                finally:
                    vhdpipe_in.close()

                pool.waitall()
            finally:
                self._clean()

    def convert_vhd_to_tar(self, vhdpipe_out, tar_file, tar_info):
        tarGenerator = AddVhdToTar(tar_file, tar_info, vhdpipe_out)
        try:
            tarGenerator.start()
        finally:
            vhdpipe_out.close()

    def _connect_request(self, vdi_ref):
        # request connection to xapi url service for VDI export
        try:
            # create task for VDI export
            label = 'VDI_EXPORT_for_' + self.instance['name']
            desc = 'Exporting VDI for instance: %s' % self.instance['name']
            self.task_ref = self.session.task.create(label, desc)
            LOG.debug("task_ref is %s" % self.task_ref)
            # connect to XS
            xs_url = urlparse.urlparse(self.host_url)
            if xs_url.scheme == 'http':
                conn = httplib.HTTPConnection(xs_url.netloc)
                LOG.debug("using http")
            elif xs_url.scheme == 'https':
                conn = httplib.HTTPSConnection(xs_url.netloc)
                LOG.debug("using https")
            vdi_export_path = utils.get_vdi_export_path(
                self.session, self.task_ref, vdi_ref)
            conn.request('GET', vdi_export_path)
            conn_resp = conn.getresponse()
        except Exception:
            LOG.debug('request connect for vdi export failed')
            raise
        return conn_resp

    def _vhd_to_pipe(self, vhd_dynDisk, vhdpipe_in):
        # Firstly write the data already parsed by vhd_dynDisk obj;
        # then write all of the remaining data to the pipe also.
        vhdpipe_in.write(vhd_dynDisk.cached_buff)
        remain_data = vhd_dynDisk.src_file
        while True:
            data = remain_data.read(CHUNK_SIZE)
            if not data:
                break
            try:
                vhdpipe_in.write(data)
            except Exception:
                LOG.debug("Failed when writing data to VHD stream.")
                raise

    def _clean(self):
        if self.conn:
            self.conn.close()
        if self.task_ref:
            self.session.task.destroy(self.task_ref)


class AddVhdToTar(object):
    def __init__(self, tar_file, tar_info, vhdpipe_out):
        self.tar_file = tar_file
        self.tar_info = tar_info
        self.stream = vhdpipe_out

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
