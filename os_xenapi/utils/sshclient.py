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
"""SSH client.

This defines a class for SSH client which can be used to scp files to
remote hosts or execute commands in remote hosts.
"""
import logging
import paramiko

from os_xenapi.client.exception import OsXenApiException
from os_xenapi.client.i18n import _

LOG = logging.getLogger(__name__)


class SshExecCmdFailure(OsXenApiException):
    msg_fmt = _("Failed to execute: %(command)s\n"
                "stdout: %(stdout)s\n"
                "stderr: %(stderr)s")


class SSHClient(object):
    def __init__(self, ip, username, password=None, pkey=None,
                 key_filename=None, log=None, look_for_keys=False,
                 allow_agent=False):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.WarningPolicy())
        self.client.connect(ip, username=username, password=password,
                            pkey=pkey, key_filename=key_filename,
                            look_for_keys=look_for_keys,
                            allow_agent=allow_agent)
        self.ip = ip
        self.log = log

    def __del__(self):
        self.client.close()

    def ssh(self, command, get_pty=True, allowed_return_codes=[0]):
        if self.log:
            self.log.debug("Executing command: [%s]" % command)
        stdin, stdout, stderr = self.client.exec_command(
            command, get_pty=get_pty)
        out = '\n'.join(stdout)
        err = '\n'.join(stderr)
        if self.log:
            if out:
                self.log.info(out)
            if err:
                self.log.error(err)
        ret = stdout.channel.recv_exit_status()
        if ret in allowed_return_codes:
            LOG.info('Swallowed acceptable return code of %d', ret)
        else:
            LOG.warn('unacceptable return code: %d', ret)
            raise SshExecCmdFailure(command=command,
                                    stdout=out, stderr=err)
        return ret, out, err

    def scp(self, source, dest):
        if self.log:
            self.log.info("Copy %s -> %s:%s" % (source, self.ip, dest))
        sftp = self.client.open_sftp()
        sftp.put(source, dest)
        sftp.close()
