# Copyright 2013 Citrix Systems
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
import socket
import sys
if sys.version_info[0] == 2:
    import httplib as httpclient
    import xmlrpclib as xmlrpcclient
else:
    import http.client as httpclient
    import xmlrpc.client as xmlrpcclient


translation = gettext.translation('xen-xm', fallback=True)

API_VERSION_1_1 = '1.1'
API_VERSION_1_2 = '1.2'


def below_python27():
    if sys.version_info[0] <= 2 and sys.version_info[1] < 7:
        return True
    else:
        return False


class Failure(Exception):
    def __init__(self, details):
        self.details = details

    def __str__(self):
        try:
            return str(self.details)
        except Exception:
            # To support py2.4/py2.7/py3 together, extract exception via sys
            # py2.4: except Exception, exn
            # py2.7/py3: except Exception as exn
            type, value = sys.exc_info()[:2]
            sys.stderr.write("%s, %s" % (type, value))
            return "Xen-API failure: %s, %s" % (type, value)

    def _details_map(self):
        return dict([(str(i), self.details[i])
                     for i in range(len(self.details))])


class UDSHTTPConnection(httpclient.HTTPConnection):
    """HTTPConnection subclass to allow HTTP over Unix domain sockets. """
    def connect(self):
        path = self.host.replace("_", "/")
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(path)


class UDSTransport(xmlrpcclient.Transport):
    def __init__(self, use_datetime=0):
        if not below_python27():
            xmlrpcclient.Transport.__init__(self, use_datetime)
        self._use_datetime = use_datetime
        self._connection = (None, None)
        self._extra_headers = []

    def add_extra_header(self, key, value):
        self._extra_headers += [(key, value)]

    def make_connection(self, host):
        if below_python27():
            # Python 2.4 compatibility
            class UDSHTTP(httpclient.HTTP):
                _connection_class = UDSHTTPConnection
            return UDSHTTP(host)
        else:
            return UDSHTTPConnection(host)

    def send_request(self, connection, handler, request_body):
        connection.putrequest("POST", handler)
        for key, value in self._extra_headers:
            connection.putheader(key, value)

# Just a "constant" that we use to decide whether to retry the RPC
_RECONNECT_AND_RETRY = object()


class Session(xmlrpcclient.ServerProxy):
    """A server proxy and session manager for communicating with xapi.

    Example:

    session = Session('http://localhost/')
    session.login_with_password('me', 'password')
    session.xenapi.VM.start(vm_uuid)
    session.xenapi.session.logout()
    """
    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                 allow_none=0):
        xmlrpcclient.ServerProxy.__init__(self, uri, transport=transport,
                                          encoding=encoding, verbose=verbose,
                                          allow_none=allow_none)
        self.transport = transport
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
                    raise xmlrpcclient.Fault(401, 'You must log in')
            else:
                return result
        raise xmlrpcclient.Fault(
            500, 'Tried 3 times to get a valid session, but failed')

    def _login(self, method, params):
        try:
            result = _parse_result(
                getattr(self, 'session.%s' % method)(*params))
            if result is _RECONNECT_AND_RETRY:
                raise xmlrpcclient.Fault(
                    500, 'Received SESSION_INVALID when logging in')
            self._session = result
            self.last_login_method = method
            self.last_login_params = params
            self.API_version = self._get_api_version()
        except socket.error:
            e = sys.exc_info()[1]
            if e.errno == socket.errno.ETIMEDOUT:
                raise xmlrpcclient.Fault(504, 'The connection timed out')
            else:
                raise e

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
        elif name == 'logout':
            return _Dispatcher(self.API_version, self.xenapi_request, "logout")
        else:
            return xmlrpcclient.ServerProxy.__getattr__(self, name)


def xapi_local():
    return Session("http://_var_xapi_xapi/", transport=UDSTransport())


def _parse_result(result):
    if type(result) != dict or 'Status' not in result:
        raise xmlrpcclient.Fault(
            500, 'Missing Status in response from server' + result)
    if result['Status'] == 'Success':
        if 'Value' in result:
            return result['Value']
        else:
            raise xmlrpcclient.Fault(
                500, 'Missing Value in response from server')
    else:
        if 'ErrorDescription' in result:
            if result['ErrorDescription'][0] == 'SESSION_INVALID':
                return _RECONNECT_AND_RETRY
            else:
                raise Failure(result['ErrorDescription'])
        else:
            raise xmlrpcclient.Fault(
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
