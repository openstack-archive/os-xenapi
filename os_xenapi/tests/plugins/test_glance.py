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
except ImportError:
    # make py3.x happy: it's needed for script parsing, although this test
    # is excluded from py3.x testing
    import http.client as httplib
    from urllib.error import HTTPError
    from urllib.error import URLError
    import urllib.request as urllib2

from os_xenapi.tests.plugins import plugin_test


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
        expected_url = "%(glance_endpoint)s/v2/images/%(image_id)s/file" % {
            'glance_endpoint': fake_endpoint,
            'image_id': 'fake_image_id'}

        self.glance._upload_tarball_by_url_v2(
            'fake_staging_path', 'fake_image_id', fake_endpoint,
            fake_extra_headers, fake_properties)

        self.assertTrue(mock_HTTPConn.called)
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers)
        self.assertTrue(mock_update_image_meta.called)
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
        expected_url = "%(glance_endpoint)s/v2/images/%(image_id)s/file" % {
            'glance_endpoint': fake_endpoint,
            'image_id': 'fake_image_id'}

        self.glance._upload_tarball_by_url_v2(
            'fake_staging_path', 'fake_image_id', fake_endpoint,
            fake_extra_headers, fake_properties)

        self.assertTrue(mock_HTTPSConn.called)
        self.assertTrue(mock_update_image_meta.called)
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPSConn.return_value.getresponse.called)
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
        expected_url = "%(glance_endpoint)s/v2/images/%(image_id)s/file" % {
            'glance_endpoint': fake_endpoint,
            'image_id': 'fake_image_id'}

        self.glance._upload_tarball_by_url_v2(
            'fake_staging_path', 'fake_image_id', fake_endpoint,
            fake_extra_headers, fake_properties)

        self.assertTrue(mock_HTTPSConn.called)
        self.assertTrue(mock_update_image_meta.called)
        mock_validate_image.assert_called_with(fake_conn,
                                               expected_url,
                                               fake_extra_headers)
        self.assertTrue(mock_create_tarball.called)
        self.assertTrue(
            mock_HTTPSConn.return_value.getresponse.called)
        self.assertTrue(mock_check_resp_status.called)
