#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_snapshot_repository

short_description: Manage Elasticsearch Snapshot Repositories.

description:
  - Manage Elasticsearch Snapshot Repositories.
  - Create and delete repostories.
  - At present no update functionality.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  location:
    description:
      - Location of the shared filesystem used to store and retrieve snapshots.
      - This location must be registered in the path.repo setting on all master and data nodes in the cluster.
    type: str
  type:
    description:
      - Repository type can include fs, source and url
    type: str
    default: fs
  state:
    description:
      - The desired state of the user.
    type: str
    choices:
      - present
      - absent
    default: present
  name:
    description:
      - The name of the repository.
    type: str
    required: yes
  verify:
    description:
      - If true, the request verifies the repository is functional on all master and data nodes in the cluster.
      - If false, this verification is skipped
    type: bool
    default: True

'''

EXAMPLES = r'''
- name: Add a snapshot repository
  community.elastic.elastic_snapshot_repository:
    name: "my_repository"
    location: "/mnt/my_backup_location"
    state: "present"

- name: Delete a snapshot repository
  community.elastic.elastic_snapshot_repository:
    name: "my_repository"
    state: "absent"
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


def get_snapshot_repository(module, client, name):
    '''
    Uses the get snapshot api to return information about the given snapshot
    '''
    try:
        response = dict(client.snapshot.get_repository(repository=name))
    except NotFoundError as excep:
        response = None
    except Exception as excep:
        module.fail_json(msg=str(excep))
    return response


def put_repository(module, client, name):
    '''
    Creates a repository
    '''
    body = {
        "type": module.params['type'],
        "settings": {
            "location": module.params['location']
        }
    }
    try:
        response = dict(client.snapshot.create_repository(repository=name,
                                                          body=body,
                                                          verify=module.params['verify']))
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
        "absent"
    ]

    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        location=dict(type='str'),
        type=dict(type='str', default='fs'),
        state=dict(type='str', choices=state_choices, default='present'),
        name=dict(type='str', required=True),
        verify=dict(type='bool', default=True)
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
    state = module.params['state']

    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        repository = get_snapshot_repository(module, client, name)
        response = None

        if repository is None:
            if state == "present":
                if module.check_mode is False:
                    response = put_repository(module, client, name)
                else:
                    response = {"aknowledged": True}
                module.exit_json(changed=True, msg="The repository {0} was successfully created: {1}".format(name, str(response)))
            elif state == "absent":
                module.exit_json(changed=False, msg="The repository {0} does not exist.".format(name))
        else:
            if state == "present":
                module.exit_json(changed=False, msg="The repository {0} already exists.".format(name))
            elif state == "absent":
                if module.check_mode is False:
                    response = client.snapshot.delete_repository(repository=name)
                else:
                    response = {"aknowledged": True}
                module.exit_json(changed=True, msg="The repository {0} was deleted: {1}".format(name, str(response)))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
