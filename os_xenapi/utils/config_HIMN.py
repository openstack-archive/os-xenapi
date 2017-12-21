#!/usr/bin/env python
import logging
import os
from sshclient import SSHClient
import subprocess
import netifaces
import sys

LOG = logging.getLogger('HIMN')

def detect_himn(eths=None):
    if eths is None:
        eths = netifaces.interfaces()
    for eth in eths:
        ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)
        if ip is None:
            continue
        himn_local = ip[0]['addr']
        himn_xs = '.'.join(himn_local.split('.')[:-1] + ['1'])
        if os.environ["DOM0-HIMN-IP"] == himn_xs:
            return eth, ip
    return None, None

def detect_interface(client):
    out = None
    if client is not None:
        out = client.ssh("Get network interface of HIMN",
                         "xe network-list name-label='Host "
                         "internal management network'  | grep 'bridge' "
                         "| awk '{print $4}'",
                         output=True).strip("\n")
    return out

class FatalException(Exception):
    pass

def reportError(err):
    LOG.error(err)
    raise FatalException(err)

def eth_to_mac(eth):
    return netifaces.ifaddresses(eth).get(netifaces.AF_LINK)[0]['addr']

def find_eth_xenstore():
    domid = execute('xenstore-read', 'domid')
    himn_mac = execute(
        'xenstore-read',
        '/local/domain/%s/vm-data/himn_mac' % domid)

    eths = [eth for eth in netifaces.interfaces()
            if eth_to_mac(eth) == himn_mac]
    if len(eths) != 1:
        reportError('Cannot find eth matches himn_mac')

    return eths[0]

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
            reportError(err)

    return proc.returncode, out, err


def execute(*cmd, **kwargs):
    _, out, _ = detailed_execute(*cmd, **kwargs)
    return out

def main(argv):
    env_set = (["DOM0-HIMN-IP", "DOM0-USER-NAME", "DOM0-PASSWD"])
    if env_set not in os.environ.keys():
        exc_log = "Environment variables missing: ip, user name, password"
        reportError(exc_log)

    eth, ip = detect_himn()
    if not ip:
        LOG.warn("Can not get himn eth from eth list, access xenstore...")
        eth = find_eth_xenstore()
    # populate the ifcfg file for HIMN interface, so that it will always get ip in the future.
    ifcfg_file = '/etc/sysconfig/network-scripts/ifcfg-%s' % eth
    s = ('DEVICE="{eth}"\n'
         'IPV6INIT="no"\n'
         'BOOTPROTO="dhcp"\n'
         'DEFROUTE=no\n'
         'ONBOOT="yes"\n'.format(eth=eth))
    with open(ifcfg_file, 'w') as f:
        f.write(s)

    client = SSHClient(os.environ["DOM0-HIMN-IP"],
                       os.environ["DOM0-USER-NAME"],
                       os.environ["DOM0-PASSWD"])
    network_interface = detect_interface(client)
    # allow traffic from HIMN and forward traffic
    execute('/usr/bin/touch', '/tmp/test_by_himn')
    execute('iptables', '-t', 'nat', '-A', 'POSTROUTING',
            '-o', network_interface, '-j', 'MASQUERADE')
    execute('iptables', '-A', 'FORWARD',
            '-i', network_interface, '-o', eth,
            '-m', 'state', '--state', 'RELATED,ESTABLISHED',
            '-j', 'ACCEPT')
    execute('iptables', '-A', 'FORWARD',
            '-i', eth, '-o', network_interface,
            '-j', 'ACCEPT')
    execute('iptables', '-A', 'INPUT', '-i', eth, '-j', 'ACCEPT')
    execute('iptables', '-t', 'filter', '-S', 'FORWARD')
    execute('iptables', '-t', 'nat', '-S', 'POSTROUTING')


if __name__ == '__main__':
    main(sys.argv[1:])
