# Copyright 2013 OpenStack Foundation
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


def copy_vdi(session, vdi_ref, vdi_size, image_id=None):
    args = {}
    args['vdi-ref'] = vdi_ref
    args['image-size'] = str(vdi_size)
    if image_id:
        args['cached-image'] = image_id
    session.call_plugin('kernel.py', 'copy_vdi', args)


def create_kernel_ramdisk(session, image_id, new_image_uuid):
    args = {}
    args['cached-image'] = image_id
    args['new-image-uuid'] = new_image_uuid
    session.call_plugin('kernel.py', 'create_kernel_ramdisk', args)


def remove_kernel_ramdisk(session, kernel_file=None, ramdisk_file=None):
    args = {}
    if kernel_file:
        args['kernel-file'] = kernel_file
    if ramdisk_file:
        args['ramdisk-file'] = ramdisk_file
    if args:
        session.call_plugin('kernel.py', 'remove_kernel_ramdisk', args)
