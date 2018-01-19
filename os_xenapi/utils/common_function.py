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

"""The common functions for XenAPI utils

It contains the common functions used by XenAPI utils."""

import inspect
import ipaddress
import logging
import netifaces
import os
import subprocess
import sys

from os_xenapi.client import exception


LOG = logging.getLogger('XenAPI_utils')


def exit_with_error(err_msg):
    sys.stderr.write(err_msg)
    sys.exit(1)


def detailed_execute(*cmd, **kwargs):
    cmd = map(str, cmd)
    _env = kwargs.get('env')
    env_prefix = ''
    if _env:
        env_prefix = ''.join(['%s=%s ' % (k, _env[k]) for k in _env])

        env = dict(os.environ)
        env.update(_env)
    else:
        env = None
    LOG.info(env_prefix + ' '.join(cmd))
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,  # nosec
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env)

    prompt = kwargs.get('prompt')
    if prompt:
        (out, err) = proc.communicate(prompt)
    else:
        (out, err) = proc.communicate()

    if out:
        # Truncate "\n" if it is the last char
        out = out.strip()
        LOG.debug(out)
    if err:
        LOG.info(err)

    if proc.returncode is not None and proc.returncode != 0:
        if proc.returncode in kwargs.get('allowed_return_codes', [0]):
            LOG.info('Swallowed acceptable return code of %d',
                     proc.returncode)
        else:
            LOG.warn('proc.returncode: %s', proc.returncode)
            raise exception.ExecuteCommandFailed(cmd)

    return proc.returncode, out, err


def execute(*cmd, **kwargs):
    _, out, _ = detailed_execute(*cmd, **kwargs)
    return out


def get_eth_ipaddr(eth):
    # return eth's IP address.
    return netifaces.ifaddresses(eth).get(netifaces.AF_INET)[0]['addr']


def get_eth_mac(eth):
    # Get eth's mac address.
    return netifaces.ifaddresses(eth).get(netifaces.AF_LINK)[0]['addr']


def get_remote_hostname(host_client):
    # Get remote host's hostname via the host_client connected to the host.
    out, _ = host_client.ssh('hostname')
    hostname = out.strip()
    return hostname


def get_host_ipv4s(host_client):
    # Get host's IPs (v4 only) via the host_client connected to the host.
    ipv4s = []
    command = "ip -4 -o addr show scope global | awk '{print $2, $4}'"
    out, _ = host_client.ssh(command)
    for line in out.split('\n'):
        line = line.strip()
        if line:
            interface, ipv4_address = line.split()
            net_if = ipaddress.IPv4Interface(ipv4_address)
            network = net_if.network
            ipv4 = {}
            ipv4['interface'] = interface
            ipv4['address'], _ = ipv4_address.split('/')
            ipv4['broadcast'] = str(network.broadcast_address)
            ipv4['network'] = str(network.network_address)
            ipv4['netmask'] = str(network.netmask)
            ipv4s.append(ipv4)

    return ipv4s


def scp_and_execute(dom0_client, script_name):
    # copy script to remote host and execute it
    TMP_SH_DIR = dom0_client.ssh("mktemp -d /tmp/domu_sh.XXXXXX", output=True)
    TMP_SH_PATH = TMP_SH_DIR + '/' + script_name
    Util_DIR = os.path.dirname(
        os.path.abspath(inspect.getfile(inspect.currentframe())))
    SH_TOOLS_DIR = Util_DIR + '/sh_tools/'
    dom0_client.ssh("mkdir -p " + TMP_SH_DIR)
    try:
        dom0_client.scp(SH_TOOLS_DIR + script_name, TMP_SH_PATH)
        dom0_client.ssh("chmod +x " + TMP_SH_PATH)
        dom0_client.ssh(TMP_SH_PATH)
    finally:
        dom0_client.ssh("rm -rf " + TMP_SH_DIR)
