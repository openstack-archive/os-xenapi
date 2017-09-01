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

import logging
import struct

from os_xenapi.client import exception as xenapi_except


LOG = logging.getLogger(__name__)


FMT_TO_LEN = {
    '!B': 1,
    '!H': 2,
    '!I': 4,
    '!Q': 8,
}

DISK_TYPE = {'None': 0,
             'Reserved_1': 1,
             'Fixed hard disk': 2,
             'Dynamic hard disk': 3,
             'Differencing hard disk': 4,
             'Reserved_5': 5,
             'Reserved_6': 6,
             }


class VHDFileParser(object):
    # This class supplies utils to parse different parts of a VHD file.
    # It follows the following VHD spec:
    # https://www.microsoft.com/en-us/download/confirmation.aspx?id=23850
    def __init__(self, file_obj):
        self.src_file = file_obj
        self.cached_buff = b''

    def get_disk_type_name(self, type_val):
        for type_name in DISK_TYPE:
            if (DISK_TYPE[type_name] == type_val):
                return type_name

    def cached_read(self, read_size):
        # the data will be cached in the buffer.
        data = self.src_file.read(read_size)
        if data:
            self.cached_buff += data
        return data

    def parse_vhd_footer(self):
        footer_raw_data = self.cached_read(VHDFooter.VHD_HDF_SIZE)
        return VHDFooter(footer_raw_data)


class VHDDynDiskParser(VHDFileParser):
    """The class presents the Dynamical Disk file:

    The Dynamic Hard Disk Image format is as below:
         +-----------------------------------------------+
         |Mirror Image of Hard drive footer (512 bytes)  |
         +-----------------------------------------------+
         |Dynamic Disk Header (1024 bytes)               |
         +-----------------------------------------------+
         | padding bytes                                 |
         |(Table Offset in Dynamic Disk Header determines|
         | where the BAT starts from)                    |
         +-----------------------------------------------+
         |BAT (Block Allocation Table)                   |
         +-----------------------------------------------+
         |Padding bytes to ensure the bitmap+Data blocks |
         |start from 512-byte sector boundary.           |
         +-----------------------------------------------+
         | bitmap 1 (512 bytes)                          |
         | Data Block 1                                  |
         +-----------------------------------------------+
         | bitmap 2 (512 bytes)                          |
         | Data Block 2                                  |
         +-----------------------------------------------+
         | ...                                           |
         +-----------------------------------------------+
         | bitmap 1 (512 bytes)                          |
         | Data Block n                                  |
         +-----------------------------------------------+
         | Hard drive footer (512 bytes)                 |
         +-----------------------------------------------+
    """

    SIZE_OF_BITMAP = 512

    def __init__(self, file_obj):
        self.src_file = file_obj
        self.cached_buff = b''
        self.footer = self.parse_vhd_footer()
        dyn_disk_type = DISK_TYPE['Dynamic hard disk']
        if self.footer.disk_type != dyn_disk_type:
            disk_type_name = self.get_disk_type_name(
                self.footer.disk_type)
            raise xenapi_except.VhdDiskTypeNotSupported(
                disk_type=disk_type_name)
        self.DynDiskHdr = self._get_dynamic_disk_header()
        self.BatPaddingData = self._get_bat_padding()
        self.Bat = self._get_block_allocation_table()

    def _get_dynamic_disk_header(self):
        ddh_raw_data = self.cached_read(VHDDynDiskHdr.VHD_DDH_SIZE)
        return VHDDynDiskHdr(ddh_raw_data)

    def _get_bat_padding(self):
        PaddingData = None
        len_padding = (self.DynDiskHdr.bat_offset - VHDFooter.VHD_HDF_SIZE -
                       VHDDynDiskHdr.VHD_DDH_SIZE)
        if len_padding > 0:
            PaddingData = self.cached_read(len_padding)
        return PaddingData

    def _get_block_allocation_table(self):
        bat_ent_size = FMT_TO_LEN[VHDBlockAllocTable.FMT_BAT_ENT]
        bat_size = bat_ent_size * self.DynDiskHdr.bat_max_entries
        raw_data = self.cached_read(bat_size)
        return VHDBlockAllocTable(raw_data)

    def get_vhd_file_size(self):
        # it will calculate the VHD file's size basing on the first
        # non data block sections. It's useful in the scenario where
        # the VHD file's data is passed via streaming. We can
        # calculate the file size before we get all data. But please
        # note it only works when the data blocks all are continuously
        # places in the VHD file (no holes). The VHD files exported
        # by invoking XenAPI should meet this prerequisite.
        # The "bitmap+Data blocks" should start from the point which is
        # after the Block Allocation Table and also meets the 512 bytes
        # boundary.
        bat_offset = self.DynDiskHdr.bat_offset
        bat_size = len(self.Bat.raw_data)
        data_offset = bat_offset + bat_size
        if data_offset % 512 != 0:
            data_offset = (data_offset / 512 + 1) * 512
        bitmap_size = VHDDynDiskParser.SIZE_OF_BITMAP
        block_size = self.DynDiskHdr.block_size
        valid_blocks = self.Bat.num_valid_bat_entries
        data_size = (bitmap_size + block_size) * valid_blocks
        file_size = data_offset + data_size + VHDFooter.VHD_HDF_SIZE
        LOG.debug("Calcuated file_size = {}: bat_offset = {}; "
                  "bat_size = {}; data_offset = {}; data_size = {}; "
                  "footer_size = {}".format(file_size, bat_offset, bat_size,
                                            data_offset, data_size,
                                            VHDFooter.VHD_HDF_SIZE))
        return file_size


class VHDFooter(object):
    # VHD Hard Disk Footer
    VHD_HDF_SIZE = 512
    HDF_LAYOUT = {
        'current_size': {
            'offset': 48,
            'format': '!Q'},
        'disk_type': {
            'offset': 60,
            'format': '!I'},
    }

    def __init__(self, raw_data):
        self.raw_data = raw_data
        self._parse_data()

    def _parse_data(self):
        hdf_layout = VHDFooter.HDF_LAYOUT
        for field in hdf_layout:
            format = hdf_layout[field]['format']
            pos_start = hdf_layout[field]['offset']
            pos_end = pos_start + FMT_TO_LEN[format]
            (value, ) = struct.unpack(format,
                                      self.raw_data[pos_start: pos_end])
            setattr(self, field, value)


class VHDDynDiskHdr(object):
    """VHD Dynamic Disk Header:

     The Dynamic Disk Header(DDH) layout is as below:
        |**fields**             | **size**|
        |Cookie                 |    8    |
        |Data Offset            |    8    |
        |*Table Offset*         |    8    |
        |Header Version         |    4    |
        |*Max Table Entries*    |    4    |
        |*Block Size*           |    4    |
        |Checksum               |    4    |
        |Parent Unique ID       |    16   |
        |Parent Time Stamp      |    4    |
        |Reserved               |    4    |
        |Parent Unicode Name    |    512  |
        |Parent Locator Entry 1 |    24   |
        |Parent Locator Entry 2 |    24   |
        |Parent Locator Entry 3 |    24   |
        |Parent Locator Entry 4 |    24   |
        |Parent Locator Entry 5 |    24   |
        |Parent Locator Entry 6 |    24   |
        |Parent Locator Entry 7 |    24   |
        |Parent Locator Entry 8 |    24   |
        |Reserved               |    256  |
    """

    VHD_DDH_SIZE = 1024
    DDH_LAYOUT = {
        'bat_offset': {
            'offset': 16,
            'format': '!Q'},
        'bat_max_entries':
            {'offset': 28,
             'format': '!I'},
        'block_size': {
            'offset': 32,
            'format': '!I'},
    }

    def __init__(self, raw_data):
        self.raw_data = raw_data
        self._parse_data()

    def _parse_data(self):
        ddh_layout = VHDDynDiskHdr.DDH_LAYOUT
        for field in ddh_layout:
            format = ddh_layout[field]['format']
            pos_start = ddh_layout[field]['offset']
            pos_end = pos_start + FMT_TO_LEN[format]
            (value,) = struct.unpack(format,
                                     self.raw_data[pos_start: pos_end])
            setattr(self, field, value)


class VHDBlockAllocTable(object):
    # VHD Block Allocation Table
    FMT_BAT_ENT = '!I'

    def __init__(self, raw_data):
        self.raw_data = raw_data
        self._parse_data()

    def _parse_data(self):
        self.num_valid_bat_entries = self.get_valid_bat_entries()

    def get_valid_bat_entries(self):
        # Calculate the number of valid BAT entries.
        # It will go through all BAT entries. Those entries whose value is not
        # the default value - 0xFFFFFFFF will be treated as valid.
        num_of_valid_bat_ent = 0
        size_of_bat_entry = FMT_TO_LEN[VHDBlockAllocTable.FMT_BAT_ENT]
        for i in range(0, len(self.raw_data), size_of_bat_entry):
            (value, ) = struct.unpack(VHDBlockAllocTable.FMT_BAT_ENT,
                                      self.raw_data[i: i + size_of_bat_entry])
            if value != 0xFFFFFFFF:
                num_of_valid_bat_ent += 1

        return num_of_valid_bat_ent
