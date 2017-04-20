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


def set_host_enabled(session, enabled):
    args = {"enabled": enabled}
    return session.call_plugin('xenhost.py', 'set_host_enabled', args)


def get_host_uptime(session):
    return session.call_plugin('xenhost.py', 'host_uptime', {})


def get_host_data(session):
    return session.call_plugin('xenhost.py', 'host_data', {})


def get_pci_type(session, pci_device):
    return session.call_plugin_serialized('xenhost.py', 'get_pci_type',
                                          pci_device)


def get_pci_device_details(session):
    return session.call_plugin_serialized('xenhost.py',
                                          'get_pci_device_details')
