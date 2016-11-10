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
#

import gettext
import http.client
import socket
import ssl
import sys
import xmlrpc.client as xmlrpclib

translation = gettext.translation('xen-xm', fallback=True)

API_VERSION_1_1 = '1.1'
API_VERSION_1_2 = '1.2'


class Failure(Exception):
    def __init__(self, details):
        self.details = details

    def __str__(self):
        try:
            return str(self.details)
        except Exception as exn:
            sys.stderr.write(exn)
            return "Xen-API failure: %s" % str(self.details)

    def _details_map(self):
        return dict([(str(i), self.details[i])
                     for i in range(len(self.details))])


class HTTPSByAddressConnection(http.client.HTTPSConnection):
    def __init__(self, addr, port, server_hostname, context=None,
                 check_hostname=False, *args, **kwargs):
        self.server_hostname = server_hostname
        if context is None:
            context = ssl.create_default_context()
        # hostname validation done separately by us
        context.check_hostname = check_hostname
        super(HTTPSByAddressConnection, self).__init__(
            addr, port, check_hostname=check_hostname, context=context,
            *args, **kwargs)

    def connect(self):
        super(HTTPSByAddressConnection, self).connect()
        try:
            ssl.match_hostname(self.sock.getpeercert(), self.server_hostname)
        except Exception:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            raise


class HTTPSByAddressTransport(xmlrpclib.SafeTransport):
    def __init__(self, server_hostname, *args, **kwargs):
        self.server_hostname = server_hostname
        return super(HTTPSByAddressTransport, self).__init__(*args, **kwargs)

    def make_connection(self, addr):
        if self._connection and addr == self._connection[0]:
            return self._connection[1]

        chost, self._extra_headers, x509 = self.get_host_info(addr)
        self._connection = addr,\
            HTTPSByAddressConnection(
                chost, None, server_hostname=self.server_hostname,
                context=self.context, **(x509 or {}))
        return self._connection[1]


# Just a "constant" that we use to decide whether to retry the RPC
_RECONNECT_AND_RETRY = object()


class Session(xmlrpclib.ServerProxy):
    """A server proxy and session manager for communicating with xapi.

    Example:
    session = Session('http://localhost/')
    session.login_with_password('me', 'mypassword')
    session.xenapi.VM.start(vm_uuid)
    session.xenapi.session.logout()
    """
    def __init__(self, uri, **kwargs):
        kwargs.setdefault("allow_none", True)
        xmlrpclib.ServerProxy.__init__(self, uri, **kwargs)
        self._session = None
        self.last_login_method = None
        self.last_login_params = None
        self.API_version = API_VERSION_1_1

    def xenapi_request(self, methodname, params):
        if methodname.startswith('login'):
            self._login(methodname, params)
            return None

        if methodname == 'logout' or methodname == 'session.logout':
            self._logout()
            return None

        retry_count = 0
        while retry_count < 3:
            full_params = (self._session,) + params
            result = _parse_result(getattr(self, methodname)(*full_params))
            if result is _RECONNECT_AND_RETRY:
                retry_count += 1
                if self.last_login_method:
                    self._login(self.last_login_method,
                                self.last_login_params)
                else:
                    raise xmlrpclib.Fault(401, 'You must log in')
            else:
                return result
        raise xmlrpclib.Fault(
            500, 'Tried 3 times to get a valid session, but failed')

    def _login(self, method, params):
        result = _parse_result(getattr(self, 'session.%s' % method)(*params))
        if result is _RECONNECT_AND_RETRY:
            raise xmlrpclib.Fault(
                500, 'Received SESSION_INVALID when logging in')
        self._session = result
        self.last_login_method = method
        self.last_login_params = params
        self.API_version = self._get_api_version()

    def _logout(self):
        try:
            if self.last_login_method.startswith("slave_local"):
                return _parse_result(self.session.local_logout(self._session))
            else:
                return _parse_result(self.session.logout(self._session))
        finally:
            self._session = None
            self.last_login_method = None
            self.last_login_params = None
            self.API_version = API_VERSION_1_1

    def _get_api_version(self):
        pool = self.xenapi.pool.get_all()[0]
        host = self.xenapi.pool.get_master(pool)
        major = self.xenapi.host.get_API_version_major(host)
        minor = self.xenapi.host.get_API_version_minor(host)
        return "%s.%s" % (major, minor)

    def __getattr__(self, name):
        if name == 'handle':
            return self._session
        elif name == 'xenapi':
            return _Dispatcher(self.API_version, self.xenapi_request, None)
        elif name.startswith('login') or name.startswith('slave_local'):
            return lambda *params: self._login(name, params)
        else:
            return xmlrpclib.ServerProxy.__getattr__(self, name)


def _parse_result(result):
    if type(result) != dict or 'Status' not in result:
        raise xmlrpclib.Fault(
            500, 'Missing Status in response from server' + result)
    if result['Status'] == 'Success':
        if 'Value' in result:
            return result['Value']
        else:
            raise xmlrpclib.Fault(
                500, 'Missing Value in response from server')
    else:
        if 'ErrorDescription' in result:
            if result['ErrorDescription'][0] == 'SESSION_INVALID':
                return _RECONNECT_AND_RETRY
            else:
                raise Failure(result['ErrorDescription'])
        else:
            raise xmlrpclib.Fault(
                500, 'Missing ErrorDescription in response from server')


# Based upon _Method from xmlrpclib.
class _Dispatcher(object):
    def __init__(self, API_version, send, name):
        self.__API_version = API_version
        self.__send = send
        self.__name = name

    def __repr__(self):
        if self.__name:
            return '<XenAPI._Dispatcher for %s>' % self.__name
        else:
            return '<XenAPI._Dispatcher>'

    def __getattr__(self, name):
        if self.__name is None:
            return _Dispatcher(self.__API_version, self.__send, name)
        else:
            return _Dispatcher(self.__API_version, self.__send,
                               "%s.%s" % (self.__name, name))

    def __call__(self, *args):
        return self.__send(self.__name, args)
