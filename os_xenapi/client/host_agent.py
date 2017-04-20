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


def version(session, arg_dict):
    return session.call_plugin('agent.py', 'version', arg_dict)


def key_init(session, arg_dict):
    return session.call_plugin('agent.py', 'key_init', arg_dict)


def agent_update(session, arg_dict):
    return session.call_plugin('agent.py', 'agentupdate', arg_dict)


def password(session, arg_dict):
    return session.call_plugin('agent.py', 'password', arg_dict)


def inject_file(session, arg_dict):
    return session.call_plugin('agent.py', 'inject_file', arg_dict)


def reset_network(session, arg_dict):
    return session.call_plugin('agent.py', 'resetnetwork', arg_dict)
