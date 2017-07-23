# Copyright 2016 Citrix Systems
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

from os_xenapi.client.i18n import _


class OsXenApiException(Exception):
    """Base OsXenapi Exception

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = _("An unknown exception occurred.")
    code = 500

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            message = self.msg_fmt % kwargs

        self.message = message
        super(OsXenApiException, self).__init__(message)

    def format_message(self):
        # NOTE(mrodden): use the first argument to the python Exception object
        # which should be our full NovaException message, (see __init__)
        return self.args[0]


class PluginRetriesExceeded(OsXenApiException):
    msg_fmt = _("Number of retries to plugin (%(num_retries)d) exceeded.")


class PluginImageNotFound(OsXenApiException):
    msg_fmt = _("Image (%(image_id)s) not found.")


class SessionLoginTimeout(OsXenApiException):
    msg_fmt = _("Unable to log in to XenAPI (is the Dom0 disk full?)")


class InvalidImage(OsXenApiException):
    msg_fmt = _("Image is invalid: details is - (%(details)s)")


class HostConnectionFailure(OsXenApiException):
    msg_fmt = _("Failed connecting to host %(host_netloc)s")


class NotFound(OsXenApiException):
    msg_fmt = _("Not found error: %s")


class VdiImportFailure(OsXenApiException):
    msg_fmt = _("Failed importing VDI from VHD stream: vdi_ref=(%(vdi_ref)s)")


class VhdDiskTypeNotSupported(OsXenApiException):
    msg_fmt = _("Not supported VHD disk type: type=(%(disk_type)s)")
