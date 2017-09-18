# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import errno
import os
import socket

import mock

from os_xenapi.client import exception
from os_xenapi.client import session
from os_xenapi.client import XenAPI
from os_xenapi.tests import base


class SessionTestCase(base.TestCase):
    @mock.patch.object(session.XenAPISession, '_verify_plugin_version')
    @mock.patch.object(session.XenAPISession, '_get_platform_version')
    @mock.patch.object(session.XenAPISession, '_create_session')
    @mock.patch.object(session.XenAPISession, '_get_product_version_and_brand')
    @mock.patch.object(socket, 'gethostbyname')
    def test_session_nova_originator(self,
                                     mock_gethostbyname,
                                     mock_version_and_brand,
                                     mock_create_session,
                                     mock_platform_version,
                                     mock_verify_plugin_version):
        concurrent = 2
        originator = 'os-xenapi-nova'
        version = '2.1'
        timeout = 10
        sess = mock.Mock()
        mock_create_session.return_value = sess
        mock_version_and_brand.return_value = ('6.5', 'XenServer')
        mock_platform_version.return_value = (2, 1, 0)
        sess.xenapi.host.get_uuid.return_value = 'fake_host_uuid'
        sess.xenapi.session.get_this_host.return_value = 'fake_host_ref'
        fake_url = 'http://someserver'
        fake_host_name = 'someserver'

        xenapi_sess = session.XenAPISession(fake_url, 'username',
                                            'password', originator=originator,
                                            concurrent=concurrent,
                                            timeout=timeout)

        sess.login_with_password.assert_called_with('username', 'password',
                                                    version, originator)
        self.assertFalse(xenapi_sess.is_slave)
        mock_gethostbyname.assert_called_with(fake_host_name)
        sess.xenapi.session.get_this_host.assert_called_once_with(sess.handle)
        sess.xenapi.PIF.get_all_records_where.assert_not_called()
        self.assertEqual('fake_host_ref', xenapi_sess.host_ref)
        self.assertEqual('fake_host_uuid', xenapi_sess.host_uuid)
        self.assertEqual(fake_url, xenapi_sess.url)

    @mock.patch.object(session.XenAPISession, '_verify_plugin_version')
    @mock.patch.object(session.XenAPISession, '_get_platform_version')
    @mock.patch.object(session.XenAPISession, '_create_session')
    @mock.patch.object(session.XenAPISession, '_get_product_version_and_brand')
    @mock.patch.object(session.XenAPISession, '_create_session_and_login')
    @mock.patch.object(socket, 'gethostbyname')
    def test_session_on_slave_node_using_host_ip(self,
                                                 mock_gethostbyname,
                                                 mock_login,
                                                 mock_version_and_brand,
                                                 mock_create_session,
                                                 mock_platform_version,
                                                 mock_verify_plugin_version):
        sess = mock.Mock()
        fake_records = {'fake_PIF_ref': {'host': 'fake_host_ref'}}
        sess.xenapi.PIF.get_all_records_where.return_value = fake_records
        sess.xenapi.host.get_uuid.return_value = 'fake_host_uuid'
        side_effects = [XenAPI.Failure(['HOST_IS_SLAVE', 'fake_master_url']),
                        sess, sess, sess]
        mock_login.side_effect = side_effects
        concurrent = 2
        originator = 'os-xenapi-nova'
        timeout = 10
        mock_version_and_brand.return_value = ('6.5', 'XenServer')
        mock_platform_version.return_value = (2, 1, 0)
        fake_url = 'http://0.0.0.0'
        fake_ip = '0.0.0.0'

        xenapi_sess = session.XenAPISession(fake_url, 'username',
                                            'password', originator=originator,
                                            concurrent=concurrent,
                                            timeout=timeout)

        self.assertTrue(xenapi_sess.is_slave)
        mock_gethostbyname.assert_called_with(fake_ip)
        self.assertEqual('fake_host_ref', xenapi_sess.host_ref)
        self.assertEqual('fake_host_uuid', xenapi_sess.host_uuid)
        self.assertEqual('http://fake_master_url', xenapi_sess.master_url)
        self.assertEqual(fake_url, xenapi_sess.url)

    @mock.patch.object(session.XenAPISession, '_verify_plugin_version')
    @mock.patch.object(session.XenAPISession, '_get_platform_version')
    @mock.patch.object(session.XenAPISession, '_create_session')
    @mock.patch.object(session.XenAPISession, '_get_product_version_and_brand')
    @mock.patch.object(session.XenAPISession, '_create_session_and_login')
    @mock.patch.object(socket, 'gethostbyname')
    def test_session_on_slave_node_using_host_name(self,
                                                   mock_gethostbyname,
                                                   mock_login,
                                                   mock_version_and_brand,
                                                   mock_create_session,
                                                   mock_platform_version,
                                                   mock_verify_plugin_version):
        sess = mock.Mock()
        fake_records = {'fake_PIF_ref': {'host': 'fake_host_ref'}}
        sess.xenapi.PIF.get_all_records_where.return_value = fake_records
        sess.xenapi.host.get_uuid.return_value = 'fake_host_uuid'
        side_effects = [XenAPI.Failure(['HOST_IS_SLAVE', 'fake_master_url']),
                        sess, sess, sess]
        mock_login.side_effect = side_effects
        concurrent = 2
        originator = 'os-xenapi-nova'

        timeout = 10
        mock_version_and_brand.return_value = ('6.5', 'XenServer')
        mock_platform_version.return_value = (2, 1, 0)
        fake_url = 'http://someserver'
        fake_host_name = 'someserver'
        fake_ip = '0.0.0.0'
        mock_gethostbyname.return_value = fake_ip
        xenapi_sess = session.XenAPISession(fake_url, 'username',
                                            'password', originator=originator,
                                            concurrent=concurrent,
                                            timeout=timeout)

        self.assertTrue(xenapi_sess.is_slave)
        mock_gethostbyname.assert_called_with(fake_host_name)
        self.assertEqual('fake_host_ref', xenapi_sess.host_ref)
        self.assertEqual('fake_host_uuid', xenapi_sess.host_uuid)
        self.assertEqual('http://fake_master_url', xenapi_sess.master_url)
        self.assertEqual(fake_url, xenapi_sess.url)

    @mock.patch.object(session.XenAPISession, '_verify_plugin_version')
    @mock.patch.object(session.XenAPISession, '_get_platform_version')
    @mock.patch.object(session.XenAPISession, '_create_session')
    @mock.patch.object(session.XenAPISession, '_get_product_version_and_brand')
    @mock.patch.object(session.XenAPISession, '_create_session_and_login')
    @mock.patch.object(socket, 'gethostbyname')
    def test_session_on_slave_node_exc_no_host_ref(self,
                                                   mock_gethostbyname,
                                                   mock_login,
                                                   mock_version_and_brand,
                                                   mock_create_session,
                                                   mock_platform_version,
                                                   mock_verify_plugin_version):
        sess = mock.Mock()
        fake_records = {}
        sess.xenapi.PIF.get_all_records_where.return_value = fake_records
        sess.xenapi.host.get_uuid.return_value = 'fake_host_uuid'
        side_effects = [XenAPI.Failure(['HOST_IS_SLAVE', 'fake_master_url']),
                        sess, sess, sess]
        mock_login.side_effect = side_effects
        concurrent = 2
        originator = 'os-xenapi-nova'

        timeout = 10
        mock_version_and_brand.return_value = ('6.5', 'XenServer')
        mock_platform_version.return_value = (2, 1, 0)
        fake_url = 'http://someserver'
        fake_host_name = 'someserver'
        fake_ip = '0.0.0.0'
        mock_gethostbyname.return_value = fake_ip

        self.assertRaises(
            XenAPI.Failure,
            session.XenAPISession,
            fake_url, 'username', 'password', originator=originator,
            concurrent=concurrent, timeout=timeout)

        mock_gethostbyname.assert_called_with(fake_host_name)

    @mock.patch.object(session.XenAPISession, '_verify_plugin_version')
    @mock.patch.object(session.XenAPISession, '_get_platform_version')
    @mock.patch.object(session.XenAPISession, '_create_session')
    @mock.patch.object(session.XenAPISession, '_get_product_version_and_brand')
    @mock.patch.object(session.XenAPISession, '_create_session_and_login')
    @mock.patch.object(socket, 'gethostbyname')
    def test_session_on_slave_node_exc_more_than_one_host_ref(
        self,
        mock_gethostbyname,
        mock_login,
        mock_version_and_brand,
        mock_create_session,
        mock_platform_version,
        mock_verify_plugin_version):
        sess = mock.Mock()
        fake_records = {'fake_PIF_ref_a': {'host': 'fake_host_ref_a'},
                        'fake_PIF_ref_b': {'host': 'fake_host_ref_b'}}
        sess.xenapi.PIF.get_all_records_where.return_value = fake_records
        sess.xenapi.host.get_uuid.return_value = 'fake_host_uuid'
        side_effects = [XenAPI.Failure(['HOST_IS_SLAVE', 'fake_master_url']),
                        sess, sess, sess]
        mock_login.side_effect = side_effects
        concurrent = 2
        originator = 'os-xenapi-nova'

        timeout = 10
        mock_version_and_brand.return_value = ('6.5', 'XenServer')
        mock_platform_version.return_value = (2, 1, 0)
        fake_url = 'http://someserver'
        fake_host_name = 'someserver'
        fake_ip = '0.0.0.0'
        mock_gethostbyname.return_value = fake_ip

        self.assertRaises(
            XenAPI.Failure,
            session.XenAPISession,
            fake_url, 'username', 'password', originator=originator,
            concurrent=concurrent, timeout=timeout)

        mock_gethostbyname.assert_called_with(fake_host_name)

    @mock.patch.object(session.XenAPISession, '_verify_plugin_version')
    @mock.patch.object(session.XenAPISession, '_get_platform_version')
    @mock.patch('eventlet.timeout.Timeout')
    @mock.patch.object(session.XenAPISession, '_create_session')
    @mock.patch.object(session.XenAPISession, '_get_product_version_and_brand')
    @mock.patch.object(socket, 'gethostbyname')
    @mock.patch.object(session.XenAPISession, '_get_host_ref')
    def test_session_login_with_timeout(self, mock_get_host_ref,
                                        mock_gethostbyname, mock_version,
                                        create_session, mock_timeout,
                                        mock_platform_version,
                                        mock_verify_plugin_version):
        concurrent = 2
        originator = 'os-xenapi-nova'
        sess = mock.Mock()
        create_session.return_value = sess
        mock_version.return_value = ('version', 'brand')
        mock_platform_version.return_value = (2, 1, 0)

        session.XenAPISession('http://someserver', 'username', 'password',
                              originator=originator, concurrent=concurrent)
        self.assertEqual(concurrent, sess.login_with_password.call_count)
        self.assertEqual(concurrent, mock_timeout.call_count)

    @mock.patch.object(session.XenAPISession, '_verify_plugin_version')
    @mock.patch.object(session.XenAPISession, 'call_plugin')
    @mock.patch.object(session.XenAPISession, '_get_software_version')
    @mock.patch.object(session.XenAPISession, '_create_session')
    @mock.patch.object(socket, 'gethostbyname')
    @mock.patch.object(session.XenAPISession, '_get_host_ref')
    def test_relax_xsm_sr_check_true(self, mock_get_host_ref,
                                     mock_gethostbyname,
                                     mock_create_session,
                                     mock_get_software_version,
                                     mock_call_plugin,
                                     mock_verify_plugin_version):
        sess = mock.Mock()
        mock_create_session.return_value = sess
        mock_get_software_version.return_value = {'product_version': '6.5.0',
                                                  'product_brand': 'XenServer',
                                                  'platform_version': '1.9.0'}
        # mark relax-xsm-sr-check=True in /etc/xapi.conf
        mock_call_plugin.return_value = "True"
        xenapi_sess = session.XenAPISession(
            'http://someserver', 'username', 'password')
        self.assertTrue(xenapi_sess.is_xsm_sr_check_relaxed())

    @mock.patch.object(session.XenAPISession, '_verify_plugin_version')
    @mock.patch.object(session.XenAPISession, 'call_plugin')
    @mock.patch.object(session.XenAPISession, '_get_software_version')
    @mock.patch.object(session.XenAPISession, '_create_session')
    @mock.patch.object(socket, 'gethostbyname')
    @mock.patch.object(session.XenAPISession, '_get_host_ref')
    def test_relax_xsm_sr_check_XS65_missing(self, mock_get_host_ref,
                                             mock_gethostbyname,
                                             mock_create_session,
                                             mock_get_software_version,
                                             mock_call_plugin,
                                             mock_verify_plugin_version):
        sess = mock.Mock()

        mock_create_session.return_value = sess
        mock_get_software_version.return_value = {'product_version': '6.5.0',
                                                  'product_brand': 'XenServer',
                                                  'platform_version': '1.9.0'}
        # mark no relax-xsm-sr-check setting in /etc/xapi.conf
        mock_call_plugin.return_value = ""
        xenapi_sess = session.XenAPISession(
            'http://someserver', 'username', 'password')
        self.assertFalse(xenapi_sess.is_xsm_sr_check_relaxed())

    @mock.patch.object(session.XenAPISession, '_verify_plugin_version')
    @mock.patch.object(session.XenAPISession, 'call_plugin')
    @mock.patch.object(session.XenAPISession, '_get_software_version')
    @mock.patch.object(session.XenAPISession, '_create_session')
    @mock.patch.object(socket, 'gethostbyname')
    @mock.patch.object(session.XenAPISession, '_get_host_ref')
    def test_relax_xsm_sr_check_XS7_missing(self, mock_get_host_ref,
                                            mock_gethostbyname,
                                            mock_create_session,
                                            mock_get_software_version,
                                            mock_call_plugin,
                                            mock_verify_plugin_version):
        sess = mock.Mock()
        mock_create_session.return_value = sess
        mock_get_software_version.return_value = {'product_version': '7.0.0',
                                                  'product_brand': 'XenServer',
                                                  'platform_version': '2.1.0'}
        # mark no relax-xsm-sr-check in /etc/xapi.conf
        mock_call_plugin.return_value = ""
        xenapi_sess = session.XenAPISession(
            'http://someserver', 'username', 'password')
        self.assertTrue(xenapi_sess.is_xsm_sr_check_relaxed())


class ApplySessionHelpersTestCase(base.TestCase):
    def setUp(self):
        super(ApplySessionHelpersTestCase, self).setUp()
        self.session = mock.Mock()
        session.apply_session_helpers(self.session)

    def test_apply_session_helpers_add_VM(self):
        self.session.VM.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("VM.get_X", "ref")

    def test_apply_session_helpers_add_SR(self):
        self.session.SR.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("SR.get_X", "ref")

    def test_apply_session_helpers_add_VDI(self):
        self.session.VDI.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("VDI.get_X", "ref")

    def test_apply_session_helpers_add_VIF(self):
        self.session.VIF.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("VIF.get_X", "ref")

    def test_apply_session_helpers_add_VBD(self):
        self.session.VBD.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("VBD.get_X", "ref")

    def test_apply_session_helpers_add_PBD(self):
        self.session.PBD.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("PBD.get_X", "ref")

    def test_apply_session_helpers_add_PIF(self):
        self.session.PIF.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("PIF.get_X", "ref")

    def test_apply_session_helpers_add_VLAN(self):
        self.session.VLAN.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("VLAN.get_X", "ref")

    def test_apply_session_helpers_add_host(self):
        self.session.host.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("host.get_X", "ref")

    def test_apply_session_helpers_add_network(self):
        self.session.network.get_X("ref")
        self.session.call_xenapi.assert_called_once_with("network.get_X",
                                                         "ref")


class CallPluginTestCase(base.TestCase):
    def _get_fake_xapisession(self):
        class FakeXapiSession(session.XenAPISession):
            def __init__(self, **kwargs):
                "Skip the superclass's dirty init"
                self.XenAPI = mock.MagicMock()

        return FakeXapiSession()

    def setUp(self):
        super(CallPluginTestCase, self).setUp()
        self.session = self._get_fake_xapisession()

    def test_serialized_with_retry_socket_error_conn_reset(self):
        exc = socket.error()
        exc.errno = errno.ECONNRESET
        plugin = 'glance'
        fn = 'download_vhd'
        num_retries = 1
        callback = None
        retry_cb = mock.Mock()
        with mock.patch.object(self.session, 'call_plugin_serialized',
                               spec=True) as call_plugin_serialized:
            call_plugin_serialized.side_effect = exc
            self.assertRaises(
                exception.PluginRetriesExceeded,
                self.session.call_plugin_serialized_with_retry, plugin, fn,
                num_retries, callback, retry_cb)
            call_plugin_serialized.assert_called_with(plugin, fn)
            self.assertEqual(2, call_plugin_serialized.call_count)
            self.assertEqual(2, retry_cb.call_count)

    def test_serialized_with_retry_socket_error_reraised(self):
        exc = socket.error()
        exc.errno = errno.ECONNREFUSED
        plugin = 'glance'
        fn = 'download_vhd'
        num_retries = 1
        callback = None
        retry_cb = mock.Mock()
        with mock.patch.object(
                self.session, 'call_plugin_serialized', spec=True)\
                as call_plugin_serialized:
            call_plugin_serialized.side_effect = exc
            self.assertRaises(
                socket.error, self.session.call_plugin_serialized_with_retry,
                plugin, fn, num_retries, callback, retry_cb)
            call_plugin_serialized.assert_called_once_with(plugin, fn)
            self.assertEqual(0, retry_cb.call_count)

    def test_serialized_with_retry_socket_reset_reraised(self):
        exc = socket.error()
        exc.errno = errno.ECONNRESET
        plugin = 'glance'
        fn = 'download_vhd'
        num_retries = 1
        callback = None
        retry_cb = mock.Mock()
        with mock.patch.object(self.session, 'call_plugin_serialized',
                               spec=True) as call_plugin_serialized:
            call_plugin_serialized.side_effect = exc
            self.assertRaises(
                exception.PluginRetriesExceeded,
                self.session.call_plugin_serialized_with_retry, plugin, fn,
                num_retries, callback, retry_cb)
            call_plugin_serialized.assert_called_with(plugin, fn)
            self.assertEqual(2, call_plugin_serialized.call_count)


class XenAPISessionTestCase(base.TestCase):
    def _get_mock_xapisession(self, software_version):
        class MockXapiSession(session.XenAPISession):
            def __init__(_ignore):
                pass

            def _get_software_version(_ignore):
                return software_version

        return MockXapiSession()

    @mock.patch.object(XenAPI, 'xapi_local')
    def test_local_session(self, mock_xapi_local):
        session = self._get_mock_xapisession({})
        session.is_local_connection = True
        mock_xapi_local.return_value = "local_connection"
        self.assertEqual("local_connection",
                         session._create_session("unix://local"))

    @mock.patch.object(XenAPI, 'Session')
    def test_remote_session(self, mock_session):
        session = self._get_mock_xapisession({})
        session.is_local_connection = False
        mock_session.return_value = "remote_connection"
        self.assertEqual("remote_connection", session._create_session("url"))

    def test_get_product_version_product_brand_does_not_fail(self):
        session = self._get_mock_xapisession(
            {'build_number': '0',
             'date': '2012-08-03',
             'hostname': 'komainu',
             'linux': '3.2.0-27-generic',
             'network_backend': 'bridge',
             'platform_name': 'XCP_Kronos',
             'platform_version': '1.6.0',
             'xapi': '1.3',
             'xen': '4.1.2',
             'xencenter_max': '1.10',
             'xencenter_min': '1.10'})

        self.assertEqual(
            ((1, 6, 0), None),
            session._get_product_version_and_brand()
        )

    def test_get_product_version_product_brand_xs_6(self):
        session = self._get_mock_xapisession(
            {'product_brand': 'XenServer',
             'product_version': '6.0.50',
             'platform_version': '0.0.1'})

        self.assertEqual(
            ((6, 0, 50), 'XenServer'),
            session._get_product_version_and_brand()
        )

    def test_verify_plugin_version_same(self):
        session = self._get_mock_xapisession({})
        session.PLUGIN_REQUIRED_VERSION = '2.4'
        with mock.patch.object(session, 'call_plugin_serialized',
                               spec=True) as call_plugin_serialized:
            call_plugin_serialized.return_value = "2.4"
            session._verify_plugin_version()

    def test_verify_plugin_version_compatible(self):
        session = self._get_mock_xapisession({})
        session.PLUGIN_REQUIRED_VERSION = '2.4'
        with mock.patch.object(session, 'call_plugin_serialized',
                               spec=True) as call_plugin_serialized:
            call_plugin_serialized.return_value = "2.5"
            session._verify_plugin_version()

    def test_verify_plugin_version_bad_maj(self):
        session = self._get_mock_xapisession({})
        session.PLUGIN_REQUIRED_VERSION = '2.4'
        with mock.patch.object(session, 'call_plugin_serialized',
                               spec=True) as call_plugin_serialized:
            call_plugin_serialized.return_value = "3.0"
            self.assertRaises(XenAPI.Failure, session._verify_plugin_version)

    def test_verify_plugin_version_bad_min(self):
        session = self._get_mock_xapisession({})
        session.PLUGIN_REQUIRED_VERSION = '2.4'
        with mock.patch.object(session, 'call_plugin_serialized',
                               spec=True) as call_plugin_serialized:
            call_plugin_serialized.return_value = "2.3"
            self.assertRaises(XenAPI.Failure, session._verify_plugin_version)

    def test_verify_current_version_matches(self):
        session = self._get_mock_xapisession({})

        # Import the plugin to extract its version
        path = os.path.dirname(__file__)
        rel_path_elem = "../../dom0/etc/xapi.d/plugins/dom0_plugin_version.py"
        for elem in rel_path_elem.split('/'):
            path = os.path.join(path, elem)
        path = os.path.realpath(path)

        plugin_version = None
        with open(path) as plugin_file:
            for line in plugin_file:
                if "PLUGIN_VERSION = " in line:
                    plugin_version = line.strip()[17:].strip('"')

        self.assertEqual(session.PLUGIN_REQUIRED_VERSION,
                         plugin_version)
