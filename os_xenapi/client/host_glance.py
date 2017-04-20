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


def download_vhd(session, num_retries, callback, retry_cb, **params):
    return session.call_plugin_serialized_with_retry(
        'glance.py', 'download_vhd2', num_retries, callback, retry_cb,
        **params)


def upload_vhd(session, num_retries, callback, retry_cb, **params):
    return session.call_plugin_serialized_with_retry(
        'glance.py', 'upload_vhd2', num_retries, callback, retry_cb, **params)
