# Copyright (c) 2017 Citrix Systems
# All Rights Reserved.
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

import mock
import sys
try:
    import httplib
    import urllib2
    from urllib2 import HTTPError
    from urllib2 import URLError
    from urlparse import urlparse
except ImportError:
    # make py3.x happy: it's needed for script parsing, although this test
    # is excluded from py3.x testing
    import http.client as httplib
    from urllib.error import HTTPError
    from urllib.error import URLError
    from urllib.parse import urlparse
    import urllib.request as urllib2
import json
from os_xenapi.tests.plugins import plugin_test


class FakeXenAPIException(Exception):
    pass


class Fake_HTTP_Request_Error(Exception):
    pass


class GlanceTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(GlanceTestCase, self).setUp()
        # md5 is deprecated in py2.7 and forward;
        sys.modules['md5'] = mock.Mock()
        self.glance = self.load_plugin("glance.py")

    @mock.patch.object(httplib, 'HTTPSConnection')
    def test_create_connection_https(self, mock_HTTPConn):
        fake_scheme = 'https'
        fake_netloc = 'fake_netloc'
        fake_https_return = mock.Mock()
        mock_HTTPConn.return_value = fake_https_return

        fake_create_Conn_return = self.glance._create_connection(
            fake_scheme, fake_netloc)
        mock_HTTPConn.assert_called_with(fake_netloc)
        mock_HTTPConn.return_value.connect.assert_called_once()
        self.assertEqual(fake_https_return, fake_create_Conn_return)

    @mock.patch.object(httplib, 'HTTPConnection')
    def test_create_connection_http(self, mock_HTTPConn):
        fake_scheme = 'http'
        fake_netloc = 'fake_netloc'
        fake_https_return = mock.Mock()
        mock_HTTPConn.return_value = fake_https_return

        fake_create_Conn_return = self.glance._create_connection(
            fake_scheme, fake_netloc)
        mock_HTTPConn.assert_called_with(fake_netloc)
        mock_HTTPConn.return_value.connect.assert_called_once()
        self.assertEqual(fake_https_return, fake_create_Conn_return)

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_and_verify_ok(self, mock_urlopen):
        mock_extract_tarball = self.mock_patch_object(
            self.glance.utils, 'extract_tarball')
        mock_md5 = mock.Mock()
        mock_md5.hexdigest.return_value = 'expect_cksum'
        mock_md5_new = self.mock_patch_object(
            self.glance.md5, 'new', mock_md5)
        mock_info = mock.Mock()
        mock_info.getheader.return_value = 'expect_cksum'
        mock_urlopen.return_value.info.return_value = mock_info
        fake_request = urllib2.Request('http://fakeurl.com')

        self.glance._download_tarball_and_verify(
            fake_request, 'fake_staging_path')
        mock_urlopen.assert_called_with(fake_request)
        mock_extract_tarball.assert_called_once()
        mock_md5_new.assert_called_once()
        mock_info.getheader.assert_called_once()
        mock_md5_new.return_value.hexdigest.assert_called_once()

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_ok_extract_failed(self, mock_urlopen):
        mock_extract_tarball = self.mock_patch_object(
            self.glance.utils, 'extract_tarball')
        fake_retcode = 0
        mock_extract_tarball.side_effect = \
            self.glance.utils.SubprocessException('fake_cmd',
                                                  fake_retcode,
                                                  'fake_out',
                                                  'fake_stderr')
        mock_md5 = mock.Mock()
        mock_md5.hexdigest.return_value = 'unexpect_cksum'
        mock_md5_new = self.mock_patch_object(
            self.glance.md5, 'new', mock_md5)
        mock_info = mock.Mock()
        mock_info.getheader.return_value = 'expect_cksum'
        mock_urlopen.return_value.info.return_value = mock_info
        fake_request = urllib2.Request('http://fakeurl.com')

        self.assertRaises(self.glance.RetryableError,
                          self.glance._download_tarball_and_verify,
                          fake_request, 'fake_staging_path'
                          )
        mock_urlopen.assert_called_with(fake_request)
        mock_extract_tarball.assert_called_once()
        mock_md5_new.assert_called_once()
        mock_info.getheader.assert_not_called()
        mock_md5_new.hexdigest.assert_not_called()

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_ok_verify_failed(self, mock_urlopen):
        mock_extract_tarball = self.mock_patch_object(
            self.glance.utils, 'extract_tarball')
        mock_md5 = mock.Mock()
        mock_md5.hexdigest.return_value = 'unexpect_cksum'
        mock_md5_new = self.mock_patch_object(
            self.glance.md5, 'new', mock_md5)
        mock_info = mock.Mock()
        mock_info.getheader.return_value = 'expect_cksum'
        mock_urlopen.return_value.info.return_value = mock_info
        fake_request = urllib2.Request('http://fakeurl.com')

        self.assertRaises(self.glance.RetryableError,
                          self.glance._download_tarball_and_verify,
                          fake_request, 'fake_staging_path'
                          )
        mock_urlopen.assert_called_with(fake_request)
        mock_extract_tarball.assert_called_once()
        mock_md5_new.assert_called_once()
        mock_md5_new.return_value.hexdigest.assert_called_once()

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_failed_HTTPError(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            None, None, None, None, None)
        fake_request = urllib2.Request('http://fakeurl.com')

        self.assertRaises(
            self.glance.RetryableError,
            self.glance._download_tarball_and_verify,
            fake_request, 'fake_staging_path')

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_failed_URLError(self, mock_urlopen):
        mock_urlopen.side_effect = URLError(None)
        fake_request = urllib2.Request('http://fakeurl.com')

        self.assertRaises(
            self.glance.RetryableError,
            self.glance._download_tarball_and_verify,
            fake_request, 'fake_staging_path')

    @mock.patch.object(urllib2, 'urlopen')
    def test_download_failed_HTTPException(self, mock_urlopen):
        mock_urlopen.side_effect = httplib.HTTPException()
        fake_request = urllib2.Request('http://fakeurl.com')

        self.assertRaises(
            self.glance.RetryableError,
            self.glance._download_tarball_and_verify,
            fake_request, 'fake_staging_path')

    @mock.patch.object(urllib2, 'Request')
    def test_download_tarball_by_url_v1(self, mock_request):
        fake_glance_endpoint = 'fake_glance_endpoint'
        fake_image_id = 'fake_extra_headers'
        expected_url = "%(glance_endpoint)s/v1/images/%(image_id)s" % {
            'glance_endpoint': fake_glance_endpoint,
            'image_id': fake_image_id}
        mock_download_tarball_and_verify = self.mock_patch_object(
            self.glance, '_download_tarball_and_verify')
        mock_request.return_value = 'fake_request'

        self.glance._download_tarball_by_url_v1(
            'fake_sr_path', 'fake_staging_path', fake_image_id,
            fake_glance_endpoint, 'fake_extra_headers')
        mock_request.assert_called_with(expected_url,
                                        headers='fake_extra_headers')
        mock_download_tarball_and_verify.assert_called_with(
            'fake_request', 'fake_staging_path')

    @mock.patch.object(urllib2, 'Request')
    def test_download_tarball_by_url_v2(self, mock_request):
        fake_glance_endpoint = 'fake_glance_endpoint'
        fake_image_id = 'fake_extra_headers'
        expected_url = "%(glance_endpoint)s/v2/images/%(image_id)s/file" % {
            'glance_endpoint': fake_glance_endpoint,
            'image_id': fake_image_id}
        mock_download_tarball_and_verify = self.mock_patch_object(
            self.glance, '_download_tarball_and_verify')
        mock_request.return_value = 'fake_request'

        self.glance._download_tarball_by_url_v2(
            'fake_sr_path', 'fake_staging_path', fake_image_id,
            fake_glance_endpoint, 'fake_extra_headers')
        mock_request.assert_called_with(expected_url,
                                        headers='fake_extra_headers')
        mock_download_tarball_and_verify.assert_called_with(
            'fake_request', 'fake_staging_path')

    def test_upload_tarball_by_url_http_v1(self):
        fake_conn = mock.Mock()
        mock_HTTPConn = self.mock_patch_object(
            self.glance, '_create_connection', fake_conn)
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload_v1')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        self.glance._create_connection().getresponse = mock.Mock()
        self.glance._create_connection().getresponse().status = httplib.OK
        fake_extra_headers = {}
        fake_properties = {}
        fake_endpoint = 'http://fake_netloc/fake_path'
        expected_url = "%(glance_endpoint)s/v1/images/%(image_id)s" % {
            'glance_endpoint': fake_endpoint,
            'image_id': 'fake_image_id'}

        self.glance._upload_tarball_by_url_v1(
            'fake_staging_path', 'fake_image_id', fake_endpoint,
            fake_extra_headers, fake_properties)

        self.assertTrue(mock_HTTPConn.called)
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPConn.return_value.getresponse.called)
        self.assertFalse(mock_check_resp_status.called)

    def test_upload_tarball_by_url_https_v1(self):
        fake_conn = mock.Mock()
        mock_HTTPSConn = self.mock_patch_object(
            self.glance, '_create_connection', fake_conn)
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload_v1')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        self.glance._create_connection().getresponse = mock.Mock()
        self.glance._create_connection().getresponse().status = httplib.OK
        fake_extra_headers = {}
        fake_properties = {}
        fake_endpoint = 'https://fake_netloc/fake_path'
        expected_url = "%(glance_endpoint)s/v1/images/%(image_id)s" % {
            'glance_endpoint': fake_endpoint,
            'image_id': 'fake_image_id'}

        self.glance._upload_tarball_by_url_v1(
            'fake_staging_path', 'fake_image_id', fake_endpoint,
            fake_extra_headers, fake_properties)

        self.assertTrue(mock_HTTPSConn.called)
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPSConn.return_value.getresponse.called)
        self.assertFalse(mock_check_resp_status.called)

    def test_upload_tarball_by_url_https_failed_retry_v1(self):
        fake_conn = mock.Mock()
        mock_HTTPSConn = self.mock_patch_object(
            self.glance, '_create_connection', fake_conn)
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload_v1')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        self.glance._create_connection().getresponse = mock.Mock()
        self.glance._create_connection().getresponse().status = \
            httplib.REQUEST_TIMEOUT
        fake_extra_headers = {}
        fake_properties = {}
        fake_endpoint = 'https://fake_netloc/fake_path'
        expected_url = "%(glance_endpoint)s/v1/images/%(image_id)s" % {
            'glance_endpoint': fake_endpoint,
            'image_id': 'fake_image_id'}

        self.glance._upload_tarball_by_url_v1(
            'fake_staging_path', 'fake_image_id', fake_endpoint,
            fake_extra_headers, fake_properties)

        self.assertTrue(mock_HTTPSConn.called)
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPSConn.return_value.getresponse.called)
        self.assertTrue(mock_check_resp_status.called)

    def test_upload_tarball_by_url_http_v2(self):
        fake_conn = mock.Mock()
        mock_HTTPConn = self.mock_patch_object(
            self.glance, '_create_connection', fake_conn)
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload_v2')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_update_image_meta = self.mock_patch_object(
            self.glance, '_update_image_meta_v2')
        self.glance._create_connection().getresponse = mock.Mock()
        self.glance._create_connection().getresponse().status = \
            httplib.NO_CONTENT
        fake_extra_headers = {}
        fake_properties = {}
        fake_endpoint = 'http://fake_netloc/fake_path'
        fake_image_id = 'fake_image_id'
        expected_url = "%(glance_endpoint)s/v2/images/%(image_id)s/file" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        expected_wsgi_path = '/fake_path/v2/images/%s' % fake_image_id
        expect_url_parts = urlparse(expected_url)

        expected_mgt_url = "%(glance_endpoint)s/v2/images/%(image_id)s" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        fake_mgt_parts = urlparse(expected_mgt_url)
        fake_mgt_path = fake_mgt_parts[2]

        self.glance._upload_tarball_by_url_v2(
            'fake_staging_path', fake_image_id, fake_endpoint,
            fake_extra_headers, fake_properties)

        mock_HTTPConn.assert_called_with(expect_url_parts[0],
                                         expect_url_parts[1])
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers,
                                               expected_wsgi_path)
        mock_update_image_meta.assert_called_with(fake_conn,
                                                  fake_extra_headers,
                                                  fake_properties,
                                                  fake_mgt_path)

        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPConn.return_value.getresponse.called)
        self.assertFalse(mock_check_resp_status.called)

    def test_upload_tarball_by_url_https_v2(self):
        fake_conn = mock.Mock()
        mock_HTTPSConn = self.mock_patch_object(
            self.glance, '_create_connection', fake_conn)
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload_v2')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_update_image_meta = self.mock_patch_object(
            self.glance, '_update_image_meta_v2')
        self.glance._create_connection().getresponse = mock.Mock()
        self.glance._create_connection().getresponse().status = \
            httplib.NO_CONTENT
        fake_extra_headers = {}
        fake_properties = {}
        fake_endpoint = 'https://fake_netloc/fake_path'
        fake_image_id = 'fake_image_id'
        expected_url = "%(glance_endpoint)s/v2/images/%(image_id)s/file" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        expect_url_parts = urlparse(expected_url)
        expected_wsgi_path = '/fake_path/v2/images/%s' % fake_image_id

        expected_mgt_url = "%(glance_endpoint)s/v2/images/%(image_id)s" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        fake_mgt_parts = urlparse(expected_mgt_url)
        fake_mgt_path = fake_mgt_parts[2]

        self.glance._upload_tarball_by_url_v2(
            'fake_staging_path', fake_image_id, fake_endpoint,
            fake_extra_headers, fake_properties)

        mock_update_image_meta.assert_called_with(fake_conn,
                                                  fake_extra_headers,
                                                  fake_properties,
                                                  fake_mgt_path)
        mock_HTTPSConn.assert_called_with(expect_url_parts[0],
                                          expect_url_parts[1])
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers,
                                               expected_wsgi_path)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPSConn.return_value.getresponse.called)
        self.assertFalse(mock_check_resp_status.called)

    def test_upload_tarball_by_url_v2_with_api_endpoint(self):
        fake_conn = mock.Mock()
        mock_Conn = self.mock_patch_object(
            self.glance, '_create_connection', fake_conn)
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload_v2')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_update_image_meta = self.mock_patch_object(
            self.glance, '_update_image_meta_v2')
        self.glance._create_connection().getresponse = mock.Mock()
        self.glance._create_connection().getresponse().status = \
            httplib.NO_CONTENT
        fake_extra_headers = {}
        fake_properties = {}
        fake_endpoint = 'https://fake_netloc:fake_port'
        fake_image_id = 'fake_image_id'
        expected_url = "%(glance_endpoint)s/v2/images/%(image_id)s/file" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        expect_url_parts = urlparse(expected_url)
        expected_api_path = '/v2/images/%s' % fake_image_id

        expected_mgt_url = "%(glance_endpoint)s/v2/images/%(image_id)s" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        fake_mgt_parts = urlparse(expected_mgt_url)
        fake_mgt_path = fake_mgt_parts[2]

        self.glance._upload_tarball_by_url_v2(
            'fake_staging_path', fake_image_id, fake_endpoint,
            fake_extra_headers, fake_properties)

        mock_update_image_meta.assert_called_with(fake_conn,
                                                  fake_extra_headers,
                                                  fake_properties,
                                                  fake_mgt_path)
        mock_Conn.assert_called_with(expect_url_parts[0], expect_url_parts[1])
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers,
                                               expected_api_path)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_Conn.return_value.getresponse.called)
        self.assertFalse(mock_check_resp_status.called)

    def test_upload_tarball_by_url_v2_with_wsgi_endpoint(self):
        fake_conn = mock.Mock()
        mock_Conn = self.mock_patch_object(
            self.glance, '_create_connection', fake_conn)
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload_v2')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_update_image_meta = self.mock_patch_object(
            self.glance, '_update_image_meta_v2')
        self.glance._create_connection().getresponse = mock.Mock()
        self.glance._create_connection().getresponse().status = \
            httplib.NO_CONTENT
        fake_extra_headers = {}
        fake_properties = {}
        fake_endpoint = 'https://fake_netloc/fake_path'
        fake_image_id = 'fake_image_id'
        expected_url = "%(glance_endpoint)s/v2/images/%(image_id)s/file" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        expect_url_parts = urlparse(expected_url)
        expected_wsgi_path = '/fake_path/v2/images/%s' % fake_image_id

        expected_mgt_url = "%(glance_endpoint)s/v2/images/%(image_id)s" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        fake_mgt_parts = urlparse(expected_mgt_url)
        fake_mgt_path = fake_mgt_parts[2]

        self.glance._upload_tarball_by_url_v2(
            'fake_staging_path', fake_image_id, fake_endpoint,
            fake_extra_headers, fake_properties)

        mock_update_image_meta.assert_called_with(fake_conn,
                                                  fake_extra_headers,
                                                  fake_properties,
                                                  fake_mgt_path)
        mock_Conn.assert_called_with(expect_url_parts[0], expect_url_parts[1])
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers,
                                               expected_wsgi_path)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_Conn.return_value.getresponse.called)
        self.assertFalse(mock_check_resp_status.called)

    def test_upload_tarball_by_url_https_failed_retry_v2(self):
        fake_conn = mock.Mock()
        mock_HTTPSConn = self.mock_patch_object(
            self.glance, '_create_connection', fake_conn)
        mock_validate_image = self.mock_patch_object(
            self.glance, 'validate_image_status_before_upload_v2')
        mock_create_tarball = self.mock_patch_object(
            self.glance.utils, 'create_tarball')
        mock_check_resp_status = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_update_image_meta = self.mock_patch_object(
            self.glance, '_update_image_meta_v2')
        self.glance._create_connection().getresponse = mock.Mock()
        self.glance._create_connection().getresponse().status = \
            httplib.REQUEST_TIMEOUT
        fake_extra_headers = {}
        fake_properties = {}
        fake_endpoint = 'https://fake_netloc/fake_path'
        fake_image_id = 'fake_image_id'
        expected_url = "%(glance_endpoint)s/v2/images/%(image_id)s/file" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        expected_wsgi_path = '/fake_path/v2/images/%s' % fake_image_id

        expected_mgt_url = "%(glance_endpoint)s/v2/images/%(image_id)s" % {
            'glance_endpoint': fake_endpoint,
            'image_id': fake_image_id}
        expect_url_parts = urlparse(expected_url)
        fake_mgt_parts = urlparse(expected_mgt_url)
        fake_mgt_path = fake_mgt_parts[2]

        self.glance._upload_tarball_by_url_v2(
            'fake_staging_path', fake_image_id, fake_endpoint,
            fake_extra_headers, fake_properties)

        mock_update_image_meta.assert_called_with(fake_conn,
                                                  fake_extra_headers,
                                                  fake_properties,
                                                  fake_mgt_path)
        mock_HTTPSConn.assert_called_with(expect_url_parts[0],
                                          expect_url_parts[1])
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers,
                                               expected_wsgi_path)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPSConn.return_value.getresponse.called)
        self.assertTrue(mock_check_resp_status.called)

    def test_update_image_meta_ok_v2_using_api_service(self):
        fake_conn = mock.Mock()
        fake_extra_headers = {'fake_type': 'fake_content'}
        fake_properties = {'fake_path': True}
        new_fake_properties = {'path': '/fake-path',
                               'value': "True",
                               'op': 'add'}
        fake_body = [
            {"path": "/container_format", "value": "ovf", "op": "add"},
            {"path": "/disk_format", "value": "vhd", "op": "add"},
            {"path": "/visibility", "value": "private", "op": "add"}]
        fake_body.append(new_fake_properties)
        fake_body_json = json.dumps(fake_body)
        fake_headers = {
            'Content-Type': 'application/openstack-images-v2.1-json-patch'}
        fake_headers.update(**fake_extra_headers)
        fake_conn.getresponse.return_value = mock.Mock()
        fake_conn.getresponse().status = httplib.OK
        expected_api_path = '/v2/images/%s' % 'fake_image_id'

        self.glance._update_image_meta_v2(fake_conn, fake_extra_headers,
                                          fake_properties, expected_api_path)
        fake_conn.request.assert_called_with('PATCH',
                                             '/v2/images/%s' % 'fake_image_id',
                                             body=fake_body_json,
                                             headers=fake_headers)
        fake_conn.getresponse.assert_called()

    def test_update_image_meta_ok_v2_using_uwsgi_service(self):
        fake_conn = mock.Mock()
        fake_extra_headers = {'fake_type': 'fake_content'}
        fake_properties = {'fake_path': True}
        new_fake_properties = {'path': '/fake-path',
                               'value': "True",
                               'op': 'add'}
        fake_body = [
            {"path": "/container_format", "value": "ovf", "op": "add"},
            {"path": "/disk_format", "value": "vhd", "op": "add"},
            {"path": "/visibility", "value": "private", "op": "add"}]
        fake_body.append(new_fake_properties)
        fake_body_json = json.dumps(fake_body)
        fake_headers = {
            'Content-Type': 'application/openstack-images-v2.1-json-patch'}
        fake_headers.update(**fake_extra_headers)
        fake_conn.getresponse.return_value = mock.Mock()
        fake_conn.getresponse().status = httplib.OK
        expected_wsgi_path = '/fake_path/v2/images/%s' % 'fake_image_id'

        self.glance._update_image_meta_v2(fake_conn, fake_extra_headers,
                                          fake_properties, expected_wsgi_path)
        fake_conn.request.assert_called_with('PATCH',
                                             '/fake_path/v2/images/%s' %
                                             'fake_image_id',
                                             body=fake_body_json,
                                             headers=fake_headers)
        fake_conn.getresponse.assert_called()

    def test_check_resp_status_and_retry_plugin_error(self):
        mock_resp_badrequest = mock.Mock()
        mock_resp_badrequest.status = httplib.BAD_REQUEST

        self.assertRaises(
            self.glance.PluginError,
            self.glance.check_resp_status_and_retry,
            mock_resp_badrequest,
            'fake_image_id',
            'fake_url')

    def test_check_resp_status_and_retry_retry_error(self):
        mock_resp_badgateway = mock.Mock()
        mock_resp_badgateway.status = httplib.BAD_GATEWAY

        self.assertRaises(
            self.glance.RetryableError,
            self.glance.check_resp_status_and_retry,
            mock_resp_badgateway,
            'fake_image_id',
            'fake_url')

    def test_check_resp_status_and_retry_image_not_found(self):
        mock_resp_badgateway = mock.Mock()
        mock_resp_badgateway.status = httplib.NOT_FOUND
        self.glance.XenAPI.Failure = FakeXenAPIException
        self.assertRaises(
            self.glance.XenAPI.Failure,
            self.glance.check_resp_status_and_retry,
            mock_resp_badgateway,
            'fake_image_id',
            'fake_url')

    def test_check_resp_status_and_retry_unknown_status(self):
        fake_unknown_http_status = -1
        mock_resp_other = mock.Mock()
        mock_resp_other.status = fake_unknown_http_status

        self.assertRaises(
            self.glance.RetryableError,
            self.glance.check_resp_status_and_retry,
            mock_resp_other,
            'fake_image_id',
            'fake_url')

    def test_validate_image_status_before_upload_ok_v1(self):
        mock_conn = mock.Mock()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        mock_check_resp_status_and_retry = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.OK
        mock_head_resp.read.return_value = 'fakeData'
        mock_head_resp.getheader.return_value = 'queued'
        mock_conn.getresponse.return_value = mock_head_resp

        self.glance.validate_image_status_before_upload_v1(
            mock_conn, fake_url, extra_headers=mock.Mock())

        self.assertTrue(mock_conn.getresponse.called)
        self.assertEqual(mock_head_resp.read.call_count, 2)
        self.assertFalse(mock_check_resp_status_and_retry.called)

    def test_validate_image_status_before_upload_image_status_error_v1(self):
        mock_conn = mock.Mock()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.OK
        mock_head_resp.read.return_value = 'fakeData'
        mock_head_resp.getheader.return_value = 'not-queued'
        mock_conn.getresponse.return_value = mock_head_resp

        self.assertRaises(self.glance.PluginError,
                          self.glance.validate_image_status_before_upload_v1,
                          mock_conn, fake_url, extra_headers=mock.Mock())
        mock_conn.request.assert_called_once()
        mock_conn.getresponse.assert_called_once()
        self.assertEqual(mock_head_resp.read.call_count, 2)

    def test_validate_image_status_before_upload_rep_body_too_long_v1(self):
        mock_conn = mock.Mock()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.OK
        mock_head_resp.read.return_value = 'fakeData longer than 8'
        mock_head_resp.getheader.return_value = 'queued'
        mock_conn.getresponse.return_value = mock_head_resp

        self.assertRaises(self.glance.RetryableError,
                          self.glance.validate_image_status_before_upload_v1,
                          mock_conn, fake_url, extra_headers=mock.Mock())
        mock_conn.request.assert_called_once()
        mock_conn.getresponse.assert_called_once()
        mock_head_resp.read.assert_called_once()

    def test_validate_image_status_before_upload_req_head_exception_v1(self):
        mock_conn = mock.Mock()
        mock_conn.request.side_effect = Fake_HTTP_Request_Error()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.OK
        mock_head_resp.read.return_value = 'fakeData'
        mock_head_resp.getheader.return_value = 'queued'
        mock_conn.getresponse.return_value = mock_head_resp

        self.assertRaises(self.glance.RetryableError,
                          self.glance.validate_image_status_before_upload_v1,
                          mock_conn, fake_url, extra_headers=mock.Mock())
        mock_conn.request.assert_called_once()
        mock_head_resp.read.assert_not_called()
        mock_conn.getresponse.assert_not_called()

    def test_validate_image_status_before_upload_unexpected_resp_v1(self):
        mock_conn = mock.Mock()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        parts = urlparse(fake_url)
        path = parts[2]
        fake_image_id = path.split('/')[-1]
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.BAD_REQUEST
        mock_head_resp.read.return_value = 'fakeData'
        mock_head_resp.getheader.return_value = 'queued'
        mock_conn.getresponse.return_value = mock_head_resp
        self.mock_patch_object(self.glance, 'check_resp_status_and_retry')

        self.glance.validate_image_status_before_upload_v1(
            mock_conn, fake_url, extra_headers=mock.Mock())
        self.assertEqual(mock_head_resp.read.call_count, 2)
        self.glance.check_resp_status_and_retry.assert_called_with(
            mock_head_resp, fake_image_id, fake_url)
        mock_conn.request.assert_called_once()

    def test_validate_image_status_before_upload_ok_v2_using_api_service(self):
        mock_conn = mock.Mock()
        fake_url = 'http://fake_host:fake_port/fake_path/fake_image_id'
        mock_check_resp_status_and_retry = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.OK
        mock_head_resp.read.return_value = '{"status": "queued"}'
        mock_conn.getresponse.return_value = mock_head_resp
        fake_extra_headers = mock.Mock()
        expected_api_path = '/v2/images/%s' % 'fake_image_id'

        self.glance.validate_image_status_before_upload_v2(
            mock_conn, fake_url, fake_extra_headers, expected_api_path)

        self.assertTrue(mock_conn.getresponse.called)
        self.assertEqual(
            mock_head_resp.read.call_count, 2)
        self.assertFalse(mock_check_resp_status_and_retry.called)
        mock_conn.request.assert_called_with('GET',
                                             '/v2/images/fake_image_id',
                                             headers=fake_extra_headers)

    def test_validate_image_status_before_upload_ok_v2_using_uwsgi(self):
        mock_conn = mock.Mock()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        mock_check_resp_status_and_retry = self.mock_patch_object(
            self.glance, 'check_resp_status_and_retry')
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.OK
        mock_head_resp.read.return_value = '{"status": "queued"}'
        mock_conn.getresponse.return_value = mock_head_resp

        fake_extra_headers = mock.Mock()
        fake_patch_path = 'fake_patch_path'

        self.glance.validate_image_status_before_upload_v2(
            mock_conn, fake_url, fake_extra_headers, fake_patch_path)

        self.assertTrue(mock_conn.getresponse.called)
        self.assertEqual(
            mock_head_resp.read.call_count, 2)
        self.assertFalse(mock_check_resp_status_and_retry.called)
        mock_conn.request.assert_called_with('GET',
                                             'fake_patch_path',
                                             headers=fake_extra_headers)

    def test_validate_image_status_before_upload_get_image_failed_v2(self):
        mock_conn = mock.Mock()
        mock_conn.request.side_effect = Fake_HTTP_Request_Error()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.OK
        mock_conn.getresponse.return_value = mock_head_resp
        expected_wsgi_path = '/fake_path/v2/images/%s' % 'fake_image_id'

        self.assertRaises(self.glance.RetryableError,
                          self.glance.validate_image_status_before_upload_v2,
                          mock_conn, fake_url, mock.Mock(), expected_wsgi_path)
        mock_conn.request.assert_called_once()
        mock_head_resp.read.assert_not_called()
        mock_conn.getresponse.assert_not_called()

    def test_validate_image_status_before_upload_unexpected_resp_v2(self):
        mock_conn = mock.Mock()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        self.mock_patch_object(self.glance, 'check_resp_status_and_retry')
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.BAD_REQUEST
        mock_conn.getresponse.return_value = mock_head_resp
        expected_wsgi_path = '/fake_path/v2/images/%s' % 'fake_image_id'

        self.glance.validate_image_status_before_upload_v2(
            mock_conn, fake_url, mock.Mock(), expected_wsgi_path)
        mock_conn.request.assert_called_once()
        mock_conn.getresponse.assert_called_once()
        mock_head_resp.read.assert_called_once()
        self.glance.check_resp_status_and_retry.assert_called_once()

    def test_validate_image_status_before_upload_failed_v2(self):
        mock_conn = mock.Mock()
        fake_url = 'http://fake_host/fake_path/fake_image_id'
        mock_head_resp = mock.Mock()
        mock_head_resp.status = httplib.OK
        mock_head_resp.read.return_value = '{"status": "not-queued"}'
        mock_conn.getresponse.return_value = mock_head_resp
        expected_wsgi_path = '/fake_path/v2/images/%s' % 'fake_image_id'

        self.assertRaises(self.glance.PluginError,
                          self.glance.validate_image_status_before_upload_v2,
                          mock_conn, fake_url, mock.Mock(), expected_wsgi_path)
        mock_conn.request.assert_called_once()
        mock_head_resp.read.assert_called_once()

    def test_download_vhd2_v1(self):
        fake_api_version = 1
        mock_make_staging_area = self.mock_patch_object(
            self.glance.utils, 'make_staging_area', 'fake_staging_path')
        mock_download_tarball_by_url = self.mock_patch_object(
            self.glance, '_download_tarball_by_url_v1')
        mock_import_vhds = self.mock_patch_object(
            self.glance.utils, 'import_vhds')
        mock_cleanup_staging_area = self.mock_patch_object(
            self.glance.utils, 'cleanup_staging_area')

        self.glance.download_vhd2(
            'fake_session', 'fake_image_id', 'fake_endpoint',
            'fake_uuid_stack', 'fake_sr_path', 'fake_extra_headers',
            fake_api_version)

        mock_make_staging_area.assert_called_with('fake_sr_path')
        mock_download_tarball_by_url.assert_called_with('fake_sr_path',
                                                        'fake_staging_path',
                                                        'fake_image_id',
                                                        'fake_endpoint',
                                                        'fake_extra_headers')
        mock_import_vhds.assert_called_with('fake_sr_path',
                                            'fake_staging_path',
                                            'fake_uuid_stack')
        mock_cleanup_staging_area.assert_called_with('fake_staging_path')

    def test_download_vhd2_v2(self):
        fake_api_version = 2
        mock_make_staging_area = self.mock_patch_object(
            self.glance.utils, 'make_staging_area', 'fake_staging_path')
        mock_download_tarball_by_url = self.mock_patch_object(
            self.glance, '_download_tarball_by_url_v2')
        mock_import_vhds = self.mock_patch_object(
            self.glance.utils, 'import_vhds')
        mock_cleanup_staging_area = self.mock_patch_object(
            self.glance.utils, 'cleanup_staging_area')

        self.glance.download_vhd2(
            'fake_session', 'fake_image_id', 'fake_endpoint',
            'fake_uuid_stack', 'fake_sr_path', 'fake_extra_headers',
            fake_api_version)

        mock_make_staging_area.assert_called_with('fake_sr_path')
        mock_download_tarball_by_url.assert_called_with('fake_sr_path',
                                                        'fake_staging_path',
                                                        'fake_image_id',
                                                        'fake_endpoint',
                                                        'fake_extra_headers')
        mock_import_vhds.assert_called_with('fake_sr_path',
                                            'fake_staging_path',
                                            'fake_uuid_stack')
        mock_cleanup_staging_area.assert_called_with('fake_staging_path')

    def test_upload_vhd2_v1(self):
        fake_api_version = 1
        mock_make_staging_area = self.mock_patch_object(
            self.glance.utils, 'make_staging_area', 'fake_staging_path')
        mock_prepare_staging_area = self.mock_patch_object(
            self.glance.utils, 'prepare_staging_area')
        mock_upload_tarball_by_url = self.mock_patch_object(
            self.glance, '_upload_tarball_by_url_v1')
        mock_cleanup_staging_area = self.mock_patch_object(
            self.glance.utils, 'cleanup_staging_area')

        self.glance.upload_vhd2(
            'fake_session', 'fake_vid_uuids', 'fake_image_id',
            'fake_endpoint', 'fake_sr_path', 'fake_extra_headers',
            'fake_properties', fake_api_version)
        mock_make_staging_area.assert_called_with('fake_sr_path')
        mock_upload_tarball_by_url.assert_called_with('fake_staging_path',
                                                      'fake_image_id',
                                                      'fake_endpoint',
                                                      'fake_extra_headers',
                                                      'fake_properties')
        mock_prepare_staging_area.assert_called_with('fake_sr_path',
                                                     'fake_staging_path',
                                                     'fake_vid_uuids')
        mock_cleanup_staging_area.assert_called_with('fake_staging_path')

    def test_upload_vhd2_v2(self):
        fake_api_version = 2
        mock_make_staging_area = self.mock_patch_object(
            self.glance.utils, 'make_staging_area', 'fake_staging_path')
        mock_prepare_staging_area = self.mock_patch_object(
            self.glance.utils, 'prepare_staging_area')
        mock_upload_tarball_by_url = self.mock_patch_object(
            self.glance, '_upload_tarball_by_url_v2')
        mock_cleanup_staging_area = self.mock_patch_object(
            self.glance.utils, 'cleanup_staging_area')

        self.glance.upload_vhd2(
            'fake_session', 'fake_vid_uuids', 'fake_image_id',
            'fake_endpoint', 'fake_sr_path', 'fake_extra_headers',
            'fake_properties', fake_api_version)

        mock_make_staging_area.assert_called_with('fake_sr_path')
        mock_upload_tarball_by_url.assert_called_with('fake_staging_path',
                                                      'fake_image_id',
                                                      'fake_endpoint',
                                                      'fake_extra_headers',
                                                      'fake_properties')
        mock_prepare_staging_area.assert_called_with('fake_sr_path',
                                                     'fake_staging_path',
                                                     'fake_vid_uuids')
        mock_cleanup_staging_area.assert_called_with('fake_staging_path')
