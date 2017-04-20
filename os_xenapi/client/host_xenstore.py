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


def read_record(session, dom_id, path, ignore_missing_path=True):
    args = {'dom_id': dom_id, 'path': path,
            'ignore_missing_path': 'True' if ignore_missing_path else 'False'}
    return session.call_plugin('xenstore.py', 'read_record', args)


def delete_record(session, dom_id, path):
    args = {'dom_id': dom_id, 'path': path}
    return session.call_plugin('xenstore.py', 'delete_record', args)


def write_record(session, dom_id, path, value):
    args = {'dom_id': dom_id, 'path': path, 'value': value}
    return session.call_plugin('xenstore.py', 'write_record', args)
