#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_role

short_description: Manage Elasticsearch user roles.

description:
  - Manage Elasticsearch user roles.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options.py

options:
  applications:
    description:
      - A list of application privilege entries.
    type: list
    elements: dict
  cluster:
    description:
      - A list of cluster privileges.
      - The cluster level actions that users with this role can execute.
    type: list
    elements: str
  global:
    description:
      - An object defining global privileges.
      - A global privilege is a form of cluster privilege that is request-aware.
    type: dict
  indices:
    description:
      - A list of indices permissions entries.
    type: list
    elements dict
  metadata:
    description:
      - Arbitrary metadata that you want to associate with the role.
    type: dict
  run_as:
    description:
      - A list of users that the owners of this role can impersonate.
    type: list
    elements: str
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
      - The name of the role
    type: str
    required: yes

'''

EXAMPLES = r'''
- name: Create a role called admin
  community.elastic.elastic_role
    name: admin
    cluster:
      - all
    indicies:
      names:
       - index1
       - index2
       - index3
      privileges:
       - all
    applications:
      - application: myapp1
        privileges:
          - admin
          - read
        resources: "*"
      - application: myapp2
        privileges:
          - admin
        resources: "*"
    run_as:
      - other_user
      - reporting_user
    metadata:
      comment: "System admin role"

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


def get_role(module, client, name):
    '''
    Uses the get roles api to return information about the given role
    '''
    try:
        response = dict(client.security.get_role(name=name))
    except NotFoundError as excep:
        response = None
    except Exception as excep:
        module.fail_json(msg=str(excep))
    return response


def put_role(module, client, name):
    '''
    Creates or updates a role
    '''
    keys = [
        "cluster",
        "indices",
        "applications",
        "run_as",
        "metadata"
    ]
    body = {}
    for k in keys:
        if module.params[k] is not None:
            body[k] = module.params[k]
    try:
        response = dict(client.security.put_role(name=name, body=body))
        if not isinstance(response, dict):  # Valid response should be a dict
            module.fail_json(msg="Invalid response received: {0}.".format(str(response)))
    except Exception as excep:
        module.fail_json(msg=str(excep))
    return response


def role_is_different(current_role, module):
    '''
    Simplified version of original function to check if role is different
    '''
    role = {
        module.params['name']: {
            "cluster": module.params['cluster'] or [],
            "indices": module.params['indices'] or [],
            "applications": module.params['applications'] or [],
            "run_as": module.params['run_as'] or [],
            "metadata": module.params['metadata'] or {}
        }
    }
    # Get rid of these default values
    current_role[module.params['name']].pop('transient_metadata', None)
    for index in current_role[module.params['name']]['indices']:
        index.pop('allow_restricted_indices', None)
    dict1 = json.dumps(current_role, sort_keys=True)
    dict2 = json.dumps(role, sort_keys=True)
    is_different = False
    if dict1 != dict2:
        is_different = True
    return is_different


def _role_is_different(current_role, module):
    '''
    Check if there are any differences in the role
    '''
    dict1 = json.dumps(module.params['applications'], sort_keys=True)
    dict2 = json.dumps(current_role.get('applications', {}), sort_keys=True)
    if dict1 is not None and dict1 != dict2:
        return True
    if len(list(set(module.params['cluster']) - set(current_role.get('cluster', set())))) > 0:
        return True
    dict1 = json.dumps(module.params['global_v'], sort_keys=True)
    dict2 = json.dumps(current_role.get('global', None), sort_keys=True)
    if dict1 is not None and dict1 != dict2:
        return True
    dict1 = json.dumps(module.params['indices'], sort_keys=True)
    dict2 = json.dumps(current_role.get('indices', None), sort_keys=True)
    if dict1 is not None and dict1 != dict2:
        return True
    dict1 = json.dumps(module.params['metadata'], sort_keys=True)
    dict2 = json.dumps(current_role.get('metadata', None), sort_keys=True)
    if dict1 is not None and dict1 != dict2:
        return True
    if len(list(set(module.params['run_as']) - set(current_role.get('run_as', set())))) > 0:
        return True


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
        applications=dict(type='list', elements='dict'),
        cluster=dict(type='list', elements='str'),
        global_v=dict(type='dict'),
        indices=dict(type='list', elements='dict'),
        metadata=dict(type='dict'),
        name=dict(type='str', required='yes'),
        run_as=dict(type='list', elements='str'),
        state=dict(type='str', choices=state_choices, default='present'),
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

        role = get_role(module, client, name)
        response = None

        if role is None:
            if state == "present":
                if module.check_mode is False:
                    response = put_role(module, client, name)
                module.exit_json(changed=True, msg="The role {0} was successfully created: {1}".format(name, str(response)))
            elif state == "absent":
                module.exit_json(changed=False, msg="The role {0} does not exist.".format(name))
        else:
            if state == "present":
                if role_is_different(role, module):
                    if module.check_mode is False:
                        response = put_role(module, client, name)
                    module.exit_json(changed=True, msg="The role {0} was successfully updated: {1}".format(name, str(response)))
                else:
                    module.exit_json(changed=False, msg="The role {0} already exists as configured.".format(name))
            elif state == "absent":
                if module.check_mode is False:
                    response = client.security.delete_role(name=name)  # TODO Check ack key?
                    module.exit_json(changed=True, msg="The role {0} was deleted.".format(name))
                else:
                    module.exit_json(changed=True, msg="The role {0} was deleted.".format(name))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
