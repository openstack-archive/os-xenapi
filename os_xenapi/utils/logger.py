# Copyright 2018 Citrix Systems
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
"""conntrack service utils

It contains the utilities relative to logging"""
import logging
import os
import sys

LOG_ROOT = '/var/log/os-xenapi'


def exit_with_error(err_msg):
    sys.stderr.write(err_msg)
    sys.exit(1)


def setup_logging(filename, folder=LOG_ROOT, log_level=logging.WARNING):
    log_file = os.path.join(folder, filename)

    if not os.path.exists(folder):
        os.mkdir(folder)

    logging.basicConfig(
        filename=log_file, level=log_level,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')


def main(*argv):
    if len(argv) != 3:
        exit_with_error("Wrong parameters input.")
        return
    filename, folder, log_level = argv
    setup_logging(filename, folder, log_level)


if __name__ == '__main__':
    main(sys.argv[1:])
