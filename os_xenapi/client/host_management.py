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


def host_reboot(session, host_uuid):
    return session.call_plugin('xenhost.py', 'host_reboot',
                               {'host_uuid': host_uuid})


def host_shutdown(session, host_uuid):
    return session.call_plugin('xenhost.py', 'host_shutdown',
                               {'host_uuid': host_uuid})


def host_join(session, compute_uuid, url, user, passwd, force, master_addr,
              master_user, master_pass):
    args = {'compute_uuid': compute_uuid,
            'url': url,
            'user': user,
            'password': passwd,
            'force': force,
            'master_addr': master_addr,
            'master_user': master_user,
            'master_pass': master_pass}
    session.call_plugin('xenhost.py', 'host_join', args)
