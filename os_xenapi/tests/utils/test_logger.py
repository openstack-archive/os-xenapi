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
import logging
import mock
import os
from os_xenapi.tests import base
from os_xenapi.utils import logger
import sys


class XenapiLoggerTestCase(base.TestCase):
    @mock.patch.object(os.path, 'join')
    @mock.patch.object(os.path, 'exists')
    @mock.patch.object(os, 'mkdir')
    @mock.patch.object(logging, 'basicConfig')
    def test_set_up_logger(self, mock_basic_conf, mock_mkdir, mock_exists,
                           mock_join):
        fake_folder = 'fake_folder/'
        fake_file = 'fake_file'
        fake_dbg_level = 'fake_dbg_level'
        fake_abs_path = '/fake_root/' + fake_folder + fake_file
        mock_join.return_value = fake_abs_path
        mock_exists.return_value = False

        logger.main(fake_file, fake_folder, fake_dbg_level)
        mock_join.assert_called_once_with(fake_folder, fake_file)
        mock_exists.assert_called_once_with(fake_folder)
        mock_mkdir.assert_called_once_with(fake_folder)
        mock_basic_conf.assert_called_once_with(filename=fake_abs_path,
                                                level=fake_dbg_level,
                                                format='%(asctime)s '
                                                '%(name)-12s %(levelname)-8s '
                                                '%(message)s')

    @mock.patch.object(logging, 'basicConfig')
    @mock.patch.object(sys, 'exit')
    def test_set_up_logger_err_exit(self, mock_exit, mock_logger):
        logger.main('test_wrong_parameters')
        mock_logger.assert_not_called()
        mock_exit.assert_called_once()
