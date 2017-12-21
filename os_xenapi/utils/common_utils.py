#!/usr/bin/env python
import logging
import os
import subprocess
import netifaces

LOG = logging.getLogger('HIMN')

class FatalException(Exception):
    pass

def reportError(err):
    LOG.error(err)
    raise FatalException(err)

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
