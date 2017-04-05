# Copyright 2017 OpenStack Foundation
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


def make_partition(session, dev, partition_start, partition_end):
    session.call_plugin_serialized('partition_utils.py', 'make_partition',
                                   dev, partition_start, partition_end)


def mkfs(session, dev, partnum, fs_type, fs_label):
    session.call_plugin_serialized('partition_utils.py', 'mkfs', dev, partnum,
                                   fs_type, fs_label)


def wait_for_dev(session, dev_path, max_seconds):
    return session.call_plugin_serialized('partition_utils.py', 'wait_for_dev',
                                          dev_path, max_seconds)
