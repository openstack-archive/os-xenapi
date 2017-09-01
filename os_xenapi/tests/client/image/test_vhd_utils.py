# Copyright 2017 Citrix Systems
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

"""This file defines the tests used to cover unit tests for VHD utils.

To ensure it's close to the real VHD file parser, strongly suggest to use
the data from a real VHD file for the fake bytes to feed the unit tests.
Initially the fake data for the tests is from the VHD file exported from
the VM which booted from the default devstack image: cirros-0.3.5-x86_64-disk.
"""

import mock
import struct

from os_xenapi.client import exception as xenapi_except
from os_xenapi.client.image import vhd_utils
from os_xenapi.tests import base


class VhdUtilsTestCase(base.TestCase):

    def test_VHDFooter(self):
        ONE_GB = 1 * 1024 * 1024 * 1024
        TYPE_DYNAMIC = 3
        footer_data = b'\x00' * 48 + struct.pack('!Q', ONE_GB) + \
                      b'\x00' * 4 + \
                      b'\x00\x00\x00\x03'

        vhd_footer = vhd_utils.VHDFooter(footer_data)

        self.assertEqual(vhd_footer.raw_data, footer_data)
        self.assertEqual(vhd_footer.current_size, ONE_GB)
        self.assertEqual(vhd_footer.disk_type, TYPE_DYNAMIC)

    def test_VHDDynDiskHdr(self):
        BAT_OFFSET = 2048
        MAX_BAT_ENTRIES = 512
        SIZE_OF_DATA_BLOCK = 2 * 1024 * 1024
        # Construct the DDH(Dynamical Disk Header) fields.
        DDH_BAT_OFFSET = struct.pack('!Q', BAT_OFFSET)
        DDH_MAX_BAT_ENTRIES = struct.pack('!I', MAX_BAT_ENTRIES)
        DDH_BLOCK_SIZE = struct.pack('!I', SIZE_OF_DATA_BLOCK)
        ddh_data = b'\x00' * 16 + DDH_BAT_OFFSET + \
                   b'\x00' * 4 + DDH_MAX_BAT_ENTRIES + \
                   DDH_BLOCK_SIZE

        vhd_dynDiskHdr = vhd_utils.VHDDynDiskHdr(ddh_data)

        self.assertEqual(vhd_dynDiskHdr.raw_data, ddh_data)
        self.assertEqual(vhd_dynDiskHdr.bat_offset, BAT_OFFSET)
        self.assertEqual(vhd_dynDiskHdr.bat_max_entries, MAX_BAT_ENTRIES)
        self.assertEqual(vhd_dynDiskHdr.block_size, SIZE_OF_DATA_BLOCK)

    def test_VHDBlockAllocTable(self):
        MAX_BAT_ENTRIES = 512
        # Construct BAT(Block Allocation Table)
        # The non 0xffffffff means a valid BAT entry. Let's give some holes.
        # At here the DATA_BAT contains 14 valid entries in the first 16
        # 4-bytes units; there are 2 holes - 0xffffffff which should be
        # ignored.
        DATA_BAT = b'\x00\x00\x00\x08\x00\x00\x50\x0d\xff\xff\xff\xff' + \
                   b'\x00\x00\x10\x09\x00\x00\x20\x0a\x00\x00\x30\x0b' + \
                   b'\x00\x00\x40\x0c\xff\xff\xff\xff\x00\x00\x60\x0e' + \
                   b'\x00\x00\x70\x0f\x00\x00\x80\x10\x00\x00\x90\x11' + \
                   b'\x00\x00\xa0\x12\x00\x00\xb0\x13\x00\x00\xc0\x14' + \
                   b'\x00\x00\xd0\x15' + \
                   b'\xff\xff\xff\xff' * (MAX_BAT_ENTRIES - 16)

        vhd_blockAllocTable = vhd_utils.VHDBlockAllocTable(DATA_BAT)

        self.assertEqual(vhd_blockAllocTable.raw_data, DATA_BAT)
        self.assertEqual(vhd_blockAllocTable.num_valid_bat_entries, 14)


class VhdFileParserTestCase(base.TestCase):

    def test_get_disk_type_name(self):
        disk_tyep_val = 3
        expect_disk_type_name = 'Dynamic hard disk'
        fake_file = 'fake_file'
        vhdParser = vhd_utils.VHDFileParser(fake_file)
        disk_type_name = vhdParser.get_disk_type_name(disk_tyep_val)

        self.assertEqual(disk_type_name, expect_disk_type_name)

    def test_get_vhd_file_size(self):
        vhd_file = mock.Mock()
        SIZE_OF_FOOTER = 512
        SIZE_OF_DDH = 1024
        SIZE_PADDING = 512
        MAX_BAT_ENTRIES = 512
        SIZE_OF_BAT_ENTRY = 4
        SIZE_OF_BITMAP = 512
        SIZE_OF_DATA_BLOCK = 2 * 1024 * 1024
        VIRTUAL_SIZE = 40 * 1024 * 1024 * 1024
        # Make fake data for VHD footer.
        DATA_FOOTER = b'\x00' * 48 + struct.pack('!Q', VIRTUAL_SIZE)
        # disk type is 3: dynamical disk.
        DATA_FOOTER += b'\x00' * 4 + b'\x00\x00\x00\x03'
        # padding bytes
        padding_len = SIZE_OF_FOOTER - len(DATA_FOOTER)
        DATA_FOOTER += b'\x00' * padding_len

        # Construct the DDH(Dynamical Disk Header) fields.
        DDH_BAT_OFFSET = struct.pack('!Q', 2048)
        DDH_MAX_BAT_ENTRIES = struct.pack('!I', MAX_BAT_ENTRIES)
        DDH_BLOCK_SIZE = struct.pack('!I', SIZE_OF_DATA_BLOCK)
        DATA_DDH = b'\x00' * 16 + DDH_BAT_OFFSET
        DATA_DDH += b'\x00' * 4 + DDH_MAX_BAT_ENTRIES
        DATA_DDH += DDH_BLOCK_SIZE
        # padding bytes for DDH
        padding_len = SIZE_OF_DDH - len(DATA_DDH)
        DATA_DDH += b'\x00' * padding_len

        # Construct the padding bytes before the Block Allocation Table.
        DATA_PADDING = b'\x00' * SIZE_PADDING
        # Construct BAT(Block Allocation Table)
        # The non 0xffffffff means a valid BAT entry. Let's give some holes.
        # At here the DATA_BAT contains 14 valid entries in the first 16
        # 4-bytes units; there are 2 holes - 0xffffffff which should be
        # ignored.
        DATA_BAT = b'\x00\x00\x00\x08\x00\x00\x50\x0d\xff\xff\xff\xff' + \
                   b'\x00\x00\x10\x09\x00\x00\x20\x0a\x00\x00\x30\x0b' + \
                   b'\x00\x00\x40\x0c\xff\xff\xff\xff\x00\x00\x60\x0e' + \
                   b'\x00\x00\x70\x0f\x00\x00\x80\x10\x00\x00\x90\x11' + \
                   b'\x00\x00\xa0\x12\x00\x00\xb0\x13\x00\x00\xc0\x14' + \
                   b'\x00\x00\xd0\x15' + \
                   b'\xff\xff\xff\xff' * (MAX_BAT_ENTRIES - 16)
        expected_size = SIZE_OF_FOOTER * 2 + SIZE_OF_DDH
        expected_size += SIZE_PADDING + SIZE_OF_BAT_ENTRY * MAX_BAT_ENTRIES
        expected_size += (SIZE_OF_BITMAP + SIZE_OF_DATA_BLOCK) * 14

        vhd_file.read.side_effect = [DATA_FOOTER,
                                     DATA_DDH,
                                     DATA_PADDING,
                                     DATA_BAT]

        vhd_parser = vhd_utils.VHDDynDiskParser(vhd_file)
        vhd_size = vhd_parser.get_vhd_file_size()

        read_call_list = vhd_file.read.call_args_list
        expected = [mock.call(SIZE_OF_FOOTER),
                    mock.call(SIZE_OF_DDH),
                    mock.call(SIZE_PADDING),
                    mock.call(SIZE_OF_BAT_ENTRY * MAX_BAT_ENTRIES),
                    ]
        self.assertEqual(expected, read_call_list)
        self.assertEqual(expected_size, vhd_size)

    def test_not_dyn_disk_exception(self):
        # If the VHD's disk type is not dynamic disk, it should raise
        # exception.
        SIZE_OF_FOOTER = 512
        vhd_file = mock.Mock()
        # disk type is 2: fixed disk.
        DATA_FOOTER = b'\x00' * 60 + b'\x00\x00\x00\x02'
        # padding bytes
        padding_len = SIZE_OF_FOOTER - len(DATA_FOOTER)
        DATA_FOOTER += b'\x00' * padding_len
        vhd_file.read.return_value = DATA_FOOTER

        self.assertRaises(xenapi_except.VhdDiskTypeNotSupported,
                          vhd_utils.VHDDynDiskParser, vhd_file)
