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


def get_console_log(session, dom_id):
    return session.call_plugin('console.py', 'get_console_log',
                               {'dom_id': dom_id})


def transfer_vhd(session, instance_uuid, host, vdi_uuid, sr_path, seq_num):
    session.call_plugin_serialized('migration.py', 'transfer_vhd',
                                   instance_uuid, host, vdi_uuid, sr_path,
                                   seq_num)


def receive_vhd(session, instance_uuid, sr_path, uuid_stack):
    return session.call_plugin_serialized('migration.py', 'move_vhds_into_sr',
                                          instance_uuid, sr_path, uuid_stack)
