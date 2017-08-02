# Copyright (c) 2016 Citrix Systems
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

from os_xenapi.client import exception
from os_xenapi.tests.plugins import plugin_test


class PartitionUtils(plugin_test.PluginTestBase):
    def setUp(self):
        super(PartitionUtils, self).setUp()
        self.pluginlib = self.load_plugin("dom0_pluginlib.py")

        # Prevent any logging to syslog
        self.mock_patch_object(self.pluginlib,
                               'configure_logging')

        self.partition_utils = self.load_plugin("partition_utils.py")

    def test_wait_for_dev_ok(self):
        mock_sleep = self.mock_patch_object(self.partition_utils.time,
                                            'sleep')
        mock_exists = self.mock_patch_object(self.partition_utils.os.path,
                                             'exists')
        mock_exists.side_effect = [False, True]
        ret = self.partition_utils.wait_for_dev('session', '/fake', 2)

        self.assertEqual(1, mock_sleep.call_count)
        self.assertEqual(ret, "/fake")

    def test_wait_for_dev_timeout(self):
        mock_sleep = self.mock_patch_object(self.partition_utils.time,
                                            'sleep')
        mock_exists = self.mock_patch_object(self.partition_utils.os.path,
                                             'exists')
        mock_exists.side_effect = [False, False, True]
        ret = self.partition_utils.wait_for_dev('session', '/fake', 2)

        self.assertEqual(2, mock_sleep.call_count)
        self.assertEqual(ret, "")

    def test_mkfs_removes_partitions_ok(self):
        mock_run = self.mock_patch_object(self.partition_utils.utils,
                                          'run_command')
        mock__mkfs = self.mock_patch_object(self.partition_utils, '_mkfs')

        self.partition_utils.mkfs('session', 'fakedev', '1', 'ext3', 'label')
        mock__mkfs.assert_called_with('ext3', '/dev/mapper/fakedevp1',
                                      'label')
        expected_calls = [mock.call(['kpartx', '-avspp', '/dev/fakedev'])]
        expected_calls.append(mock.call(['kpartx', '-dvspp', '/dev/fakedev']))
        mock_run.assert_has_calls(expected_calls)

    def test_mkfs_removes_partitions_exc(self):
        mock_run = self.mock_patch_object(self.partition_utils.utils,
                                          'run_command')
        mock__mkfs = self.mock_patch_object(self.partition_utils, '_mkfs')
        mock__mkfs.side_effect = exception.OsXenApiException(
            message="partition failed")

        self.assertRaises(exception.OsXenApiException,
                          self.partition_utils.mkfs,
                          'session', 'fakedev', '1', 'ext3', 'label')
        expected_calls = [mock.call(['kpartx', '-avspp', '/dev/fakedev'])]
        expected_calls.append(mock.call(['kpartx', '-dvspp', '/dev/fakedev']))
        mock_run.assert_has_calls(expected_calls)

    def test_mkfs_ext3_no_label(self):
        mock_run = self.mock_patch_object(self.partition_utils.utils,
                                          'run_command')

        self.partition_utils._mkfs('ext3', '/dev/sda1', None)
        mock_run.assert_called_with(['mkfs', '-t', 'ext3', '-F', '/dev/sda1'])

    def test_mkfs_ext3(self):
        mock_run = self.mock_patch_object(self.partition_utils.utils,
                                          'run_command')

        self.partition_utils._mkfs('ext3', '/dev/sda1', 'label')
        mock_run.assert_called_with(['mkfs', '-t', 'ext3', '-F', '-L',
                                     'label', '/dev/sda1'])

    def test_mkfs_swap(self):
        mock_run = self.mock_patch_object(self.partition_utils.utils,
                                          'run_command')

        self.partition_utils._mkfs('swap', '/dev/sda1', 'ignored')
        mock_run.assert_called_with(['mkswap', '/dev/sda1'])

    def test_make_partition_sfdisk_v213(self):
        mock_run = self.mock_patch_object(self.partition_utils.utils,
                                          'run_command')
        mock_get_version = self.mock_patch_object(
            self.partition_utils, '_get_sfdisk_version')
        mock_get_version.return_value = '2.13'

        self.partition_utils.make_partition('session', 'dev', 'start', '-')

        mock_get_version.assert_called_with()
        mock_run.assert_called_with(['sfdisk', '-uS', '/dev/dev'], 'start,;\n')

    def test_make_partition_sfdisk_v223(self):
        mock_run = self.mock_patch_object(self.partition_utils.utils,
                                          'run_command')
        mock_get_version = self.mock_patch_object(
            self.partition_utils, '_get_sfdisk_version')
        mock_get_version.return_value = '2.23'

        self.partition_utils.make_partition('session', 'dev', 'start', '-')

        mock_get_version.assert_called_with()
        mock_run.assert_called_with(['sfdisk', '--force', '-uS', '/dev/dev'],
                                    'start,;\n')

    def test_make_partition_sfdisk_v226(self):
        mock_run = self.mock_patch_object(self.partition_utils.utils,
                                          'run_command')
        mock_get_version = self.mock_patch_object(
            self.partition_utils, '_get_sfdisk_version')
        mock_get_version.return_value = '2.26'

        self.partition_utils.make_partition('session', 'dev', 'start', '-')

        mock_get_version.assert_called_with()
        mock_run.assert_called_with(['sfdisk', '-uS', '/dev/dev'], 'start,;\n')

    def test_get_sfdisk_version_213pre7(self):
        mock_run = self.mock_patch_object(
            self.partition_utils.utils, 'run_command')
        mock_run.return_value = 'sfdisk (util-linux 2.13-pre7)'

        version = self.partition_utils._get_sfdisk_version()

        mock_run.assert_called_with(['/sbin/sfdisk', '-v'])
        self.assertEqual(version, '2.13')

    def test_get_sfdisk_version_223(self):
        mock_run = self.mock_patch_object(
            self.partition_utils.utils, 'run_command')
        mock_run.return_value = 'sfdisk from util-linux 2.23.2\n'

        version = self.partition_utils._get_sfdisk_version()

        mock_run.assert_called_with(['/sbin/sfdisk', '-v'])
        self.assertEqual(version, '2.23')
