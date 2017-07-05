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

from os_xenapi.client import exception
from os_xenapi.client import XenAPI


def download_vhd(session, num_retries, callback, retry_cb, image_id, sr_path,
                 extra_headers, uuid_stack=''):
    args = {'image_id': image_id, 'sr_path': sr_path,
            'extra_headers': extra_headers, 'uuid_stack': uuid_stack}
    return session.call_plugin_serialized_with_retry(
        'glance.py', 'download_vhd2', num_retries, callback, retry_cb, **args)


def upload_vhd(session, num_retries, callback, retry_cb, image_id, sr_path,
               extra_headers, vdi_uuids='', properties={}):
    args = {'image_id': image_id, 'sr_path': sr_path,
            'extra_headers': extra_headers, 'vdi_uuids': vdi_uuids,
            'properties': properties}
    try:
        session.call_plugin_serialized_with_retry(
            'glance.py', 'upload_vhd2', num_retries,
            callback, retry_cb, **args)
    except XenAPI.Failure as exc:
        if (len(exc.details) == 4 and exc.details[3] == 'ImageNotFound'):
            raise exception.PluginImageNotFound(image_id=image_id)
        else:
            raise
