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


def version(session, uuid, dom_id, timeout):
    args = {'id': uuid, 'dom_id': dom_id, 'timeout': timeout}
    return session.call_plugin('agent.py', 'version', args)


def key_init(session, uuid, dom_id, timeout, pub=''):
    args = {'id': uuid, 'dom_id': dom_id, 'timeout': timeout,
            'pub': pub}
    return session.call_plugin('agent.py', 'key_init', args)


def agent_update(session, uuid, dom_id, timeout, url='', md5sum=''):
    args = {'id': uuid, 'dom_id': dom_id, 'timeout': timeout,
            'url': url, 'md5sum': md5sum}
    return session.call_plugin('agent.py', 'agentupdate', args)


def password(session, uuid, dom_id, timeout, enc_pass=''):
    args = {'id': uuid, 'dom_id': dom_id, 'timeout': timeout,
            'enc_pass': enc_pass}
    return session.call_plugin('agent.py', 'password', args)


def inject_file(session, uuid, dom_id, timeout, b64_path='', b64_contents=''):
    args = {'id': uuid, 'dom_id': dom_id, 'timeout': timeout,
            'b64_path': b64_path, 'b64_contents': b64_contents}
    return session.call_plugin('agent.py', 'inject_file', args)


def reset_network(session, uuid, dom_id, timeout):
    args = {'id': uuid, 'dom_id': dom_id, 'timeout': timeout}
    return session.call_plugin('agent.py', 'resetnetwork', args)
