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
import mock
from os_xenapi.client import exception
from os_xenapi.tests import base
from os_xenapi.utils import conntrack_service


class XenapiConntrackServiceTestCase(base.TestCase):
    def test_ensure_conntrack_packages(self):
        client = mock.Mock()
        cmd = "if ! yum list installed conntrack-tools; then\n"  \
              "    mkdir -p /tmp/repo/;\n"  \
              "    cp /etc/yum.repos.d/CentOS-Base.repo /tmp/repo/;\n" \
              "    sed -i s/#baseurl=/baseurl=/g /tmp/repo/CentOS-Base.repo" \
              "        ;\n" \
              "    centos_ver=$(yum version nogroups |grep Installed | cut " \
              "-d' '         -f 2 | cut -d'/' -f 1 | cut -d'-' -f 1);\n" \
              "    yum install -y -c /tmp/repo/ --enablerepo=base " \
              "        --releasever=$centos_ver conntrack-tools;\n" \
              "    rm -rf TMP_REPO_DIR;\n" \
              "fi\n"

        conntrack_service.ensure_conntrack_packages(client)
        client.ssh.assert_called_once_with(cmd)

    @mock.patch.object(conntrack_service, 'ensure_conntrack_packages')
    def test_enable_conntrack_service(self, mock_ensure_conntrack):
        client = mock.Mock()
        client.ssh.side_effect = [['fake_conf_list', None], None, None, None]
        expect_cmd = "if ! ls /etc/conntrackd/conntrackd.conf.back;  then\n" \
                     "    cp -p /etc/conntrackd/conntrackd.conf " \
                     "/etc/conntrackd/conntrackd.conf.back\n" \
                     "fi\n"
        expect_cmd += "cp fake_conf_list /etc/conntrackd/conntrackd.conf\n"
        expect_call1 = mock.call('find /usr/share/doc -name '
                                 'conntrackd.conf | grep stats')
        expect_call2 = mock.call(expect_cmd)
        expect_cmd = "cat >/etc/logrotate.d/conntrackd <<EOF\n" \
                     "/var/log/conntrackd*.log {\n" \
                     "    daily\n" \
                     "    maxsize 50M\n" \
                     "    rotate 7\n" \
                     "    copytruncate\n" \
                     "    missingok\n" \
                     "}\n" \
                     "EOF"
        expect_call3 = mock.call(expect_cmd)
        expect_call4 = mock.call('service conntrackd restart')

        conntrack_service.enable_conntrack_service(client)
        client.ssh.assert_has_calls([expect_call1, expect_call2,
                                     expect_call3, expect_call4])

    @mock.patch.object(conntrack_service, 'ensure_conntrack_packages')
    def test_enable_conntrack_service_no_config(self, mock_ensure_conntrack):
        client = mock.Mock()
        client.ssh.side_effect = [[None, None], ]
        expect_cmd = 'find /usr/share/doc -name conntrackd.conf | grep stats'

        self.assertRaises(exception.NotFound,
                          conntrack_service.enable_conntrack_service,
                          client)
        client.ssh.assert_called_once_with(expect_cmd)
