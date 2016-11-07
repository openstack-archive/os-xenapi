# Copyright 2013 OpenStack Foundation
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
    """Base OsXenApi Exception for use

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = _("An unknown exception occurred.")

    def __init__(self, details=None, **kwargs):
        self.kwargs = kwargs

        if not details:
            details = self.msg_fmt % kwargs
        self.details = details
        super(OsXenApiException, self).__init__(details)

    def _details_map(self):
        return dict([(str(i), self.details[i])
                     for i in range(len(self.details))])


class PluginRetriesExceeded(OsXenApiException):
    msg_fmt = _("Number of retries to plugin (%(num_retries)d) exceeded.")


class SessionLoginTimeout(OsXenApiException):
    msg_fmt = _("Unable to log in to XenAPI (is the Dom0 disk full?)")


class VersionIncompetible(OsXenApiException):
    msg_fmt = _("Plugin version mismatch (Expected %(expected_version)s, "
                "got %(current_version)s)")


class InvalidObjectUuid(OsXenApiException):
    msg_fmt = _("Invalid UUID of %(object_type)s")


class CommandExecutionTimeout(OsXenApiException):
    msg_fmt = _("Command execution timeout")


class CommandNotImplemented(OsXenApiException):
    msg_fmt = _("This command is not implemented in Dom0")


class CommandNotFound(OsXenApiException):
    msg_fmt = _("This command is not found in Dom0")
