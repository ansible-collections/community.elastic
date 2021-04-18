#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_snapshot

short_description: Manage Elasticsearch Snapshots.

description:
  - Manage Elasticsearch Snapshots.
  - Create, delete, restore and clone snapshots.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  indices:
    description:
      - A list of indexes to include in the the snapshot.
      - By default, a snapshot includes all data streams and indices in the cluster.
      - If this argument is provided, the snapshot only includes the specified data streams and clusters.
    type: list
    elements: str
  ignore_unavailable:
    description:
      - If false, the request returns an error for any data stream or index that is missing or closed.
      - If true, the request ignores data streams and indices in indices that are missing or closed.
    type: bool
    default: false
  repository:
    description:
      - Snapshot repository name.
    type: str
    required: true
  state:
    description:
      - The desired state of the snapshot.
    type: str
    choices:
      - present
      - absent
      - clone
      - restore
    default: present
  metadata:
    description:
      - Attaches arbitrary metadata to the snapshot.
    type: str
  name:
    description:
      - The name of the snapshot.
    type: str
    required: yes
  partial:
    description:
      - If false, the entire snapshot will fail if one or more indices included in the snapshot do not have all primary shards available.
    type: bool
    default: False

'''

EXAMPLES = r'''
- name: Create a snapshot
  community.elastic.elastic_repository:
    name: "my_snapshot"
    repository: "my_repository"
    location: "/mnt/my_backup_location"
    state: "present"

- name: Delete a snapshot
  community.elastic.elastic_snapshot:
    name: "my_snapshot"
    repository: "my_repository"
    state: "absent"

- name: Snapshot specific indexes
  community.elastic.elastic_repository:
    name: "my_snapshot"
    repository: "my_repository"
    indices:
      - "myindex1"
      - "myindex2"
    location: "/mnt/my_backup_location"
    state: "present"

- name: Restore a snpashot
  community.elastic.elastic_repository:
    name: "my_snapshot"
    repository: "my_repository"
    state: "restore"
'''

RETURN = r'''
'''
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import json


from ansible_collections.community.elastic.plugins.module_utils.elastic_common import (
    missing_required_lib,
    elastic_found,
    E_IMP_ERR,
    elastic_common_argument_spec,
    ElasticHelpers,
    NotFoundError
)


def get_snapshot(module, client, repository, name):
    '''
    Uses the get snapshot api to return information about the given snapshot
    '''
    try:
        response = dict(client.snapshot.get(repository=repository,
                                            snapshot=name))
    except NotFoundError as excep:
        response = None
    except Exception as excep:
        module.fail_json(msg=str(excep))
    return response


def create_snapshot(module, client, repository, name):
    '''
    Creates a snapshot in the given repository
    '''
    body = {
        "ignore_unavailable": module.params['ignore_unavailable'],
        "metadata": module.params['metadata'],
        "partial": module.params['partial']
    }
    if module.params['indices'] is not None:
        body['indices'] = module.params['indices']
    try:
        response = dict(client.snapshot.create(repository=repository,
                                               snapshot=name,
                                               body=body))
        if not isinstance(response, dict):  # Valid response should be a dict
            module.fail_json(msg="Invalid response received: {0}.".format(str(response)))
    except Exception as excep:
        module.fail_json(msg=str(excep))
    return response


def restore_snapshot(module, client, repository, name):
    '''
    Restore an elastic snapshot
    '''
    body = {
        "ignore_unavailable": module.params['ignore_unavailable'],
        "partial": module.params['partial']
    }
    if module.params['indices'] is not None:
        body['indices'] = module.params['indices']
    try:
        response = dict(client.snapshot.restore(repository=repository,
                                                snapshot=name,
                                                body=body))
        if not isinstance(response, dict):  # Valid response should be a dict
            module.fail_json(msg="Invalid response received: {0}.".format(str(response)))
    except Exception as excep:
        module.fail_json(msg=str(excep))
    return response


# ================
# Module execution
#

def main():

    state_choices = [
        "present",
        "absent",
        "clone",
        "restore"
    ]

    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        indices=dict(type='list', elements='str'),
        ignore_unavailable=dict(type='bool', default=False),
        repository=dict(type='str', required=True),
        state=dict(type='str', choices=state_choices, default='present'),
        metadata=dict(type='str'),
        name=dict(type='str', required=True),
        partial=dict(type='bool', default=False)
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[['login_user', 'login_password']],
    )

    if not elastic_found:
        module.fail_json(msg=missing_required_lib('elasticsearch'),
                         exception=E_IMP_ERR)

    name = module.params['name']
    repository = module.params['repository']
    state = module.params['state']

    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        snapshot = get_snapshot(module, client, repository, name)
        response = None

        if snapshot is None:
            if state == "present":
                if module.check_mode is False:
                    response = create_snapshot(module, client, repository, name)
                else:
                    response = {"aknowledged": True}
                module.exit_json(changed=True, msg="The snapshot {0} was successfully created: {1}".format(name, str(response)))
            elif state == "absent":
                module.exit_json(changed=False, msg="The snapshot {0} does not exist.".format(name))
            elif state == "restore":
                module.fail_json(msg="Cannot restore a snapshot that does not exist: {0}".format(name))
        else:
            if state == "present":
                module.exit_json(changed=False, msg="The snapshot {0} already exists.".format(name))
            elif state == "absent":
                if module.check_mode is False:
                    response = client.snapshot.delete(repository=repository, snapshot=name)
                else:
                    response = {"aknowledged": True}
                module.exit_json(changed=True, msg="The snapshot {0} was deleted: {1}".format(name, str(response)))
            elif state == "restore":
                if module.check_mode is False:
                    response = restore_snapshot(module, client, repository, name)
                else:
                    response = {"aknowledged": True}
                module.exit_json(changed=True, msg="The snapshot {0} was restored: {1}".format(name, str(response)))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
