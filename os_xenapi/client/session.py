# Copyright 2013 OpenStack Foundation
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

import ast
import contextlib

try:
    import cPickle as pickle
except ImportError:
    import pickle

import errno
import socket
import time

from eventlet import queue
from eventlet import timeout
from oslo_log import log as logging
from oslo_utils import versionutils
from six.moves import http_client
from six.moves import urllib

try:
    import xmlrpclib
except ImportError:
    import six.moves.xmlrpc_client as xmlrpclib

from os_xenapi.client import exception
from os_xenapi.client.i18n import _
from os_xenapi.client.i18n import _LW
from os_xenapi.client import objects as cli_objects
from os_xenapi.client import XenAPI

LOG = logging.getLogger(__name__)


def apply_session_helpers(session):
    session.VM = cli_objects.VM(session)
    session.SR = cli_objects.SR(session)
    session.VDI = cli_objects.VDI(session)
    session.VIF = cli_objects.VIF(session)
    session.VBD = cli_objects.VBD(session)
    session.PBD = cli_objects.PBD(session)
    session.PIF = cli_objects.PIF(session)
    session.VLAN = cli_objects.VLAN(session)
    session.host = cli_objects.Host(session)
    session.network = cli_objects.Network(session)
    session.pool = cli_objects.Pool(session)
    session.task = cli_objects.Task(session)


class XenAPISession(object):
    """The session to invoke XenAPI SDK calls."""

    # This is not a config option as it should only ever be
    # changed in development environments.
    # MAJOR VERSION: Incompatible changes with the plugins
    # MINOR VERSION: Compatible changes, new plguins, etc
    PLUGIN_REQUIRED_VERSION = '2.1'

    def __init__(self, url, user, pw, originator="os-xenapi", timeout=10,
                 concurrent=5):
        """Initialize session for connection with XenServer/Xen Cloud Platform

        :param url: URL for connection to XenServer/Xen Cloud Platform
        :param user: Username for connection to XenServer/Xen Cloud Platform
        :param pw: Password for connection to XenServer/Xen Cloud Platform
        :param originator: Specify the caller for this API
        :param timeout: Timeout in seconds for XenAPI login
        :param concurrent: Maximum concurrent XenAPI connections
        """
        self.XenAPI = XenAPI
        self.originator = originator
        self.timeout = timeout
        self.concurrent = concurrent
        self._sessions = queue.Queue()
        self.host_checked = False
        self.is_slave = False
        self.ip = self._get_ip_from_url(url)
        self.url = url
        self.master_url = self._create_first_session(url, user, pw)
        self._populate_session_pool(self.master_url, user, pw)
        self.host_ref = self._get_host_ref(self.ip)
        self.host_uuid = self._get_host_uuid()
        self.product_version, self.product_brand = \
            self._get_product_version_and_brand()
        self._verify_plugin_version()
        self.platform_version = self._get_platform_version()
        self._cached_xsm_sr_relaxed = None

        apply_session_helpers(self)

    def _login_with_password(self, user, pw, session):
        login_exception = XenAPI.Failure(_("Unable to log in to XenAPI "
                                           "(is the Dom0 disk full?)"))
        with timeout.Timeout(self.timeout, login_exception):
            session.login_with_password(user, pw, self.PLUGIN_REQUIRED_VERSION,
                                        self.originator)

    def _verify_plugin_version(self):
        requested_version = self.PLUGIN_REQUIRED_VERSION
        current_version = self.call_plugin_serialized(
            'dom0_plugin_version.py', 'get_version')

        if not versionutils.is_compatible(requested_version, current_version):
            raise XenAPI.Failure(
                _("Plugin version mismatch (Expected %(exp)s, got %(got)s)") %
                {'exp': requested_version, 'got': current_version})

    def _create_first_session(self, url, user, pw):
        try:
            session = self._create_session_and_login(url, user, pw)
        except XenAPI.Failure as e:
            # if user and pw of the master are different, we're doomed!
            if e.details[0] == 'HOST_IS_SLAVE':
                master = e.details[1]
                url = self.swap_xapi_host(url, master)
                session = self._create_session_and_login(url, user, pw)
                self.is_slave = True
            else:
                raise
        self._sessions.put(session)
        return url

    def _get_ip_from_url(self, url):
        url_parts = urllib.parse.urlparse(url)
        return socket.gethostbyname(url_parts.netloc)

    def swap_xapi_host(self, url, host_addr):
        """Replace the XenServer address present in 'url' with 'host_addr'."""
        temp_url = urllib.parse.urlparse(url)
        return url.replace(temp_url.hostname, '%s' % host_addr)

    def _populate_session_pool(self, url, user, pw):
        for i in range(self.concurrent - 1):
            session = self._create_session_and_login(url, user, pw)
            self._sessions.put(session)

    def _get_host_uuid(self):
        with self._get_session() as session:
            return session.xenapi.host.get_uuid(self.host_ref)

    def _get_product_version_and_brand(self):
        """Return tuple of (major, minor, rev)

        This tuple is for host version and product brand.
        """

        software_version = self._get_software_version()
        product_version_str = software_version.get('product_version')
        # Product version is only set in some cases (e.g. XCP, XenServer) and
        # not in others (e.g. xenserver-core, XAPI-XCP).
        # In these cases, the platform version is the best number to use.
        if product_version_str is None:
            product_version_str = software_version.get('platform_version',
                                                       '0.0.0')
        product_brand = software_version.get('product_brand')
        product_version =\
            versionutils.convert_version_to_tuple(product_version_str)

        return product_version, product_brand

    def _get_platform_version(self):
        """Return a tuple of (major, minor, rev) for the host version"""
        software_version = self._get_software_version()
        platform_version_str = software_version.get('platform_version',
                                                    '0.0.0')
        platform_version = versionutils.convert_version_to_tuple(
            platform_version_str)
        return platform_version

    def _get_software_version(self):
        return self.call_xenapi('host.get_software_version', self.host_ref)

    def get_session_id(self):
        """Return a string session_id.  Used for vnc consoles."""
        with self._get_session() as session:
            return str(session._session)

    @contextlib.contextmanager
    def _get_session(self):
        """Return exclusive session for scope of with statement."""
        session = self._sessions.get()
        try:
            yield session
        finally:
            self._sessions.put(session)

    def _get_host_ref(self, host_ip):
        with self._get_session() as session:
            if self.is_slave:
                rec_dict = session.xenapi.PIF.get_all_records_where(
                    'field "IP"="%s"' % host_ip)
                if not rec_dict:
                    raise XenAPI.Failure(
                        ("ERROR, couldn't find host ref with ip \
                        %(slave_ip)s ") % {'slave_ip': host_ip})
                if len(rec_dict) > 1:
                    raise XenAPI.Failure(
                        ("ERROR, find more than one host ref with ip \
                        %(slave_ip)s ") % {'slave_ip': host_ip})
                value = list(rec_dict.values())[0]
                return value['host']
            else:
                return session.xenapi.session.get_this_host(session.handle)

    def call_xenapi(self, method, *args):
        """Call the specified XenAPI method on a background thread."""
        with self._get_session() as session:
            return session.xenapi_request(method, args)

    def call_plugin(self, plugin, fn, args):
        """Call host.call_plugin on a background thread."""
        # NOTE(armando): pass the host uuid along with the args so that
        # the plugin gets executed on the right host when using XS pools
        args['host_uuid'] = self.host_uuid

        if not plugin.endswith('.py'):
            plugin = '%s.py' % plugin

        with self._get_session() as session:
            return self._unwrap_plugin_exceptions(
                session.xenapi.host.call_plugin,
                self.host_ref, plugin, fn, args)

    def call_plugin_serialized(self, plugin, fn, *args, **kwargs):
        params = {'params': pickle.dumps(dict(args=args, kwargs=kwargs))}
        rv = self.call_plugin(plugin, fn, params)
        return pickle.loads(rv)

    def call_plugin_serialized_with_retry(self, plugin, fn, num_retries,
                                          callback, retry_cb=None, *args,
                                          **kwargs):
        """Allows a plugin to raise RetryableError so we can try again."""
        attempts = num_retries + 1
        sleep_time = 0.5
        for attempt in range(1, attempts + 1):
            try:
                if attempt > 1:
                    time.sleep(sleep_time)
                    sleep_time = min(2 * sleep_time, 15)

                callback_result = None
                if callback:
                    callback_result = callback(kwargs)

                msg = ('%(plugin)s.%(fn)s attempt %(attempt)d/%(attempts)d, '
                       'callback_result: %(callback_result)s')
                LOG.debug(msg,
                          {'plugin': plugin, 'fn': fn, 'attempt': attempt,
                           'attempts': attempts,
                           'callback_result': callback_result})
                return self.call_plugin_serialized(plugin, fn, *args, **kwargs)
            except XenAPI.Failure as exc:
                if self._is_retryable_exception(exc, fn):
                    LOG.warning(_LW('%(plugin)s.%(fn)s failed. '
                                    'Retrying call.'),
                                {'plugin': plugin, 'fn': fn})
                    if retry_cb:
                        retry_cb(exc=exc)
                else:
                    raise
            except socket.error as exc:
                if exc.errno == errno.ECONNRESET:
                    LOG.warning(_LW('Lost connection to XenAPI during call to '
                                    '%(plugin)s.%(fn)s.  Retrying call.'),
                                {'plugin': plugin, 'fn': fn})
                    if retry_cb:
                        retry_cb(exc=exc)
                else:
                    raise

        raise exception.PluginRetriesExceeded(num_retries=num_retries)

    def _is_retryable_exception(self, exc, fn):
        _type, method, error = exc.details[:3]
        if error == 'RetryableError':
            LOG.debug("RetryableError, so retrying %(fn)s", {'fn': fn},
                      exc_info=True)
            return True
        if "signal" in method:
            LOG.debug("Error due to a signal, retrying %(fn)s", {'fn': fn},
                      exc_info=True)
            return True
        else:
            return False

    def _create_session(self, url):
        """Stubout point. This can be replaced with a mock session."""
        self.is_local_connection = url == "unix://local"
        if self.is_local_connection:
            return XenAPI.xapi_local()
        return XenAPI.Session(url)

    def _create_session_and_login(self, url, user, pw):
        session = self._create_session(url)
        self._login_with_password(user, pw, session)
        return session

    def _unwrap_plugin_exceptions(self, func, *args, **kwargs):
        """Parse exception details."""
        try:
            return func(*args, **kwargs)
        except XenAPI.Failure as exc:
            LOG.debug("Got exception: %s", exc)
            if (len(exc.details) == 4 and
                exc.details[0] == 'XENAPI_PLUGIN_EXCEPTION' and
                    exc.details[2] == 'Failure'):
                params = None
                try:
                    params = ast.literal_eval(exc.details[3])
                except Exception:
                    raise exc
                raise XenAPI.Failure(params)
            else:
                raise
        except xmlrpclib.ProtocolError as exc:
            LOG.debug("Got exception: %s", exc)
            raise

    def get_rec(self, record_type, ref):
        try:
            return self.call_xenapi('%s.get_record' % record_type, ref)
        except XenAPI.Failure as e:
            if e.details[0] != 'HANDLE_INVALID':
                raise

        return None

    def get_all_refs_and_recs(self, record_type):
        """Retrieve all refs and recs for a Xen record type.

        Handles race-conditions where the record may be deleted between
        the `get_all` call and the `get_record` call.
        """

        return self.call_xenapi('%s.get_all_records' % record_type).items()

    @contextlib.contextmanager
    def custom_task(self, label, desc=''):
        """Return exclusive session for scope of with statement."""
        name = '%s-%s' % (self.originator, label)
        task_ref = self.call_xenapi("task.create", name, desc)
        try:
            LOG.debug('Created task %s with ref %s', name, task_ref)
            yield task_ref
        finally:
            self.call_xenapi("task.destroy", task_ref)
            LOG.debug('Destroyed task ref %s', task_ref)

    @contextlib.contextmanager
    def http_connection(self):
        conn = None

        xs_url = urllib.parse.urlparse(self.url)
        LOG.debug("Creating http(s) connection to %s", self.url)
        if xs_url.scheme == 'http':
            conn = http_client.HTTPConnection(xs_url.netloc)
        elif xs_url.scheme == 'https':
            conn = http_client.HTTPSConnection(xs_url.netloc)

        conn.connect()
        try:
            yield conn
        finally:
            conn.close()

    def is_xsm_sr_check_relaxed(self):
        if self._cached_xsm_sr_relaxed is None:
            config_value = self.call_plugin('config_file', 'get_val',
                                            dict(key='relax-xsm-sr-check'))
            if not config_value:
                version_str = '.'.join(str(v) for v in self.platform_version)
                if versionutils.is_compatible('2.1.0', version_str,
                                              same_major=False):
                    self._cached_xsm_sr_relaxed = True
                else:
                    self._cached_xsm_sr_relaxed = False
            else:
                self._cached_xsm_sr_relaxed = config_value.lower() == 'true'

        return self._cached_xsm_sr_relaxed
