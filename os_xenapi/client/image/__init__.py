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

from os_xenapi.client.image import vdi_handler


def stream_to_vdis(context, session, instance, host_url, data):
    handler = vdi_handler.ImageStreamToVDIs(context, session, instance,
                                            host_url, data)
    handler.start()
    return handler.vdis


def stream_from_vdis(context, session, instance, host_url, vdi_uuids):
    handler = vdi_handler.GenerateImageStream(context, session, instance,
                                              host_url, vdi_uuids)
    return handler.get_image_data()
