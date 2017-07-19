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

from eventlet import greenio
import httplib
import logging
import os
import struct
import tarfile
import urlparse

from os_xenapi.client import utils

LOG = logging.getLogger(__name__)


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


class ImageStreamToVDI(ImageCommand):
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
                sr_ref, vdi_ref = self._createVDI(
                    self.session, self.instance, virtual_size)
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
            LOG.debug("using http")
        elif self.host_url.scheme == 'https':
            conn = httplib.HTTPSConnection(self.host_url.netloc)
            LOG.debug("using https")

        vdi_import_path = self.get_vdi_import_path(
            self.session, self.task_ref, vdi_ref)
        try:
            conn.connect()
        except Exception:
            LOG.debug('Failed connecting to %s', self.host_url.netloc)
            raise

        try:
            CHUNK_SIZE = 16 * 1024
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
            LOG.debug('failed to stream vhd to vdi - vdi_ref:%s', vdi_ref)
            raise
        finally:
            resp = conn.getresponse()
            LOG.debug("the connection response status:reason is "
                      "%(status)s:%(reason)s",
                      {'status': resp.status, 'reason': resp.reason})
            conn.close()


def create_from_stream(context, session, instance, host_url, data):
    handler = ImageStreamToVDI(context, session, instance, host_url, data)
    handler.start()
    return handler.vdis
