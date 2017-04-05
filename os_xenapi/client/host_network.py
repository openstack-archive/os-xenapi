# Copyright 2013 Citrix Systems
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


def ovs_create_port(session, bridge, port, iface_id, mac, status):
    args = {'cmd': 'ovs_create_port',
            'args': {'bridge': bridge,
                     'port': port,
                     'iface-id': iface_id,
                     'mac': mac,
                     'status': status}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def ovs_add_port(session, bridge, port):
    args = {'cmd': 'ovs_add_port',
            'args': {'bridge_name': bridge, 'port_name': port}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def ovs_del_port(session, bridge, port):
    args = {'cmd': 'ovs_del_port',
            'args': {'bridge_name': bridge, 'port_name': port}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def ovs_del_br(session, bridge_name):
    args = {'cmd': 'ovs_del_br',
            'args': {'bridge_name': bridge_name}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def brctl_add_if(session, bridge_name, interface_name):
    args = {'cmd': 'brctl_add_if',
            'args': {'bridge_name': bridge_name,
                     'interface_name': interface_name}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def brctl_del_if(session, bridge_name, interface_name):
    args = {'cmd': 'brctl_del_if',
            'args': {'bridge_name': bridge_name,
                     'interface_name': interface_name}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def brctl_del_br(session, bridge_name):
    args = {'cmd': 'brctl_del_br',
            'args': {'bridge_name': bridge_name}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def brctl_add_br(session, bridge_name):
    args = {'cmd': 'brctl_add_br',
            'args': {'bridge_name': bridge_name}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def brctl_set_fd(session, bridge_name, fd):
    args = {'cmd': 'brctl_set_fd',
            'args': {'bridge_name': bridge_name,
                     'fd': fd}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def brctl_set_stp(session, bridge_name, stp_opt):
    args = {'cmd': 'brctl_set_stp',
            'args': {'bridge_name': bridge_name,
                     'option': stp_opt}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def ip_link_add_veth_pair(session, dev1_name, dev2_name):
    args = {'cmd': 'ip_link_add_veth_pair',
            'args': {'dev1_name': dev1_name,
                     'dev2_name': dev2_name}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def ip_link_del_dev(session, device):
    args = {'cmd': 'ip_link_del_dev',
            'args': {'device_name': device}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def ip_link_get_dev(session, device):
    args = {'cmd': 'ip_link_get_dev',
            'args': {'device_name': device}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def ip_link_set_dev(session, device, option):
    args = {'cmd': 'ip_link_set_dev',
            'args': {'device_name': device,
                     'option': option}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def ip_link_set_promisc(session, device, promisc_option):
    args = {'cmd': 'ip_link_set_promisc',
            'args': {'device_name': device,
                     'option': promisc_option}
            }
    session.call_plugin_serialized('xenhost.py', 'network_config', args)


def fetch_all_bandwidth(session):
    return session.call_plugin_serialized('bandwidth.py',
                                          'fetch_all_bandwidth')
