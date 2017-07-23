# Copyright 2017 Citrix Systems.
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

from oslo_log import log as logging

from os_xenapi.client import exception

LOG = logging.getLogger(__name__)


def get_default_sr(session):
    pool_ref = session.call_xenapi('pool.get_all')[0]
    sr_ref = session.call_xenapi('pool.get_default_SR', pool_ref)
    if sr_ref:
        return sr_ref
    else:
        raise exception.NotFound(_('Cannot find default SR'))


def create_vdi(session, sr_ref, instance, name_label, disk_type, virtual_size,
               read_only=False):
    """Create a VDI record and returns its reference."""
    vdi_ref = session.call_xenapi(
        "VDI.create",
        {'name_label': name_label,
         'name_description': disk_type,
         'SR': sr_ref,
         'virtual_size': str(virtual_size),
         'type': 'User',
         'sharable': False,
         'read_only': read_only,
         'xenstore_data': {},
         'other_config': _get_vdi_other_config(disk_type, instance=instance),
         'sm_config': {},
         'tags': []}
    )
    LOG.debug('Created VDI %(vdi_ref)s (%(name_label)s,'
              ' %(virtual_size)s, %(read_only)s) on %(sr_ref)s.',
              {'vdi_ref': vdi_ref, 'name_label': name_label,
               'virtual_size': virtual_size, 'read_only': read_only,
               'sr_ref': sr_ref})
    return vdi_ref


def _get_vdi_other_config(disk_type, instance=None):
    """Return metadata to store in VDI's other_config attribute.

    `nova_instance_uuid` is used to associate a VDI with a particular instance
    so that, if it becomes orphaned from an unclean shutdown of a
    compute-worker, we can safely detach it.
    """
    other_config = {'nova_disk_type': disk_type}

    # create_vdi may be called simply while creating a volume
    # hence information about instance may or may not be present
    if instance:
        other_config['nova_instance_uuid'] = instance['uuid']

    return other_config
