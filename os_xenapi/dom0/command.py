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


def ovs_create_port(session, bridge, port, iface_id, mac):
    args = {'cmd': 'ovs_create_port',
            'args': {'bridge': bridge,
                     'port': port,
                     'iface-id': iface_id,
                     'mac': mac,
                     'status': 'active',
                     'xs-vif-uuid': iface_id}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)

