#!/usr/bin/env python
import logging
import os
import subprocess
import netifaces
from os_xenapi.client import exception

LOG = logging.getLogger('common_utils')

def eth_to_mac(eth):
    return netifaces.ifaddresses(eth).get(netifaces.AF_LINK)[0]['addr']

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
            raise exception(err)

    return proc.returncode, out, err


def execute(*cmd, **kwargs):
    _, out, _ = detailed_execute(*cmd, **kwargs)
    return out
