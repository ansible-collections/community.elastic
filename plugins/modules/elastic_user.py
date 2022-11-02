#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_user

short_description: Manage Elasticsearch users.

description:
  - Manage Elasticsearchusers.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  enabled:
    description:
      - Specifies whether the user is enabled.
    type: bool
    default: true
  email:
    description:
      - The email of the user.
    type: str
  full_name:
    description:
      - The full name of the user.
    type: str
  metadata:
    description:
      - Arbitrary metadata that you want to associate with the user.
    type: dict
  password:
    description:
      -  The user's password.
    type: str
  roles:
    description:
      - A set of roles the user has.
    type: list
    elements: str
  run_as:
    description:
      - LIst of users that this user can impersonate.
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
  update_password:
    default: always
    choices: [always, on_create]
    description:
      - C(always) will always update passwords and cause the module to return changed.
      - C(on_create) will only set the password for newly created users.
    type: str
  name:
    description:
      - Username of the user.
    type: str
    required: yes
    default: {}

'''

EXAMPLES = r'''
- name: Add a user
  community.elastic.elastic_user:
    username: rhysmeister
    password: s3cr3t
    full_name: Rhys Campbell
    email: madeupemail@nowhere.ch
    roles:
      - admin
      - reporting

- name: Delete a user
  community.elastic.elastic_user:
    username: rhysmeister
    state: absent
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


def get_user(module, client, name):
    '''
    Uses the get user api to return information about the given user
    '''
    try:
        response = dict(client.security.get_user(username=name))
    except NotFoundError as excep:
        response = None
    except Exception as excep:
        module.fail_json(msg=str(excep))
    return response


def put_user(module, client, name):
    '''
    Creates or updates a user
    '''
    keys = [
        "enabled",
        "email",
        "full_name",
        "metadata",
        "password",
        "roles"
    ]
    body = {}
    for k in keys:
        if module.params[k] is not None:
            body[k] = module.params[k]
    try:
        response = dict(client.security.put_user(username=name, body=body))
        if not isinstance(response, dict):  # Valid response should be a dict
            module.fail_json(msg="Invalid response received: {0}.".format(str(response)))
    except Exception as excep:
        module.fail_json(msg=str(excep))
    return response


def user_is_different(current_user, module):
    '''
    Check if user is different
    '''
    name = module.params['name']
    user = {
        name: {
            "username": module.params['name'],
            "roles": module.params['roles'] or [],
            "enabled": module.params['enabled']
        }
    }
    if module.params['full_name'] is not None:
        user[name]['full_name'] = module.params['full_name']
    if module.params['email'] is not None:
        user[name]['email'] = module.params['email']
    if module.params['metadata'] is not None:
        user[name]['metadata'] = module.params['metadata']
    dict1 = json.dumps(current_user, sort_keys=True)
    dict2 = json.dumps(user, sort_keys=True)
    is_different = False
    if dict1 != dict2:
        is_different = True
    return is_different


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
        enabled=dict(type='bool', default=True),
        email=dict(type='str'),
        full_name=dict(type='str'),
        metadata=dict(type='dict', default={}),
        password=dict(type='str', no_log=True),
        roles=dict(type='list', elements='str'),
        name=dict(type='str', required=True),
        run_as=dict(type='list', elements='str'),
        state=dict(type='str', choices=state_choices, default='present'),
        update_password=dict(type='str', choices=['always', 'on_create'], default='always', no_log=True)
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
    update_password = module.params['update_password']

    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        user = get_user(module, client, name)
        response = None

        if user is None:
            if state == "present":
                if module.check_mode is False:
                    response = put_user(module, client, name)
                module.exit_json(changed=True, msg="The user {0} was successfully created: {1}".format(name, str(response)))
            elif state == "absent":
                module.exit_json(changed=False, msg="The user {0} does not exist.".format(name))
        else:
            if state == "present":
                if user_is_different(user, module) or update_password == "always":
                    if module.check_mode is False:
                        response = put_user(module, client, name)
                    module.exit_json(changed=True, msg="The user {0} was successfully updated: {1} {2}".format(name, str(response), str(user)))
                else:
                    module.exit_json(changed=False, msg="The user {0} already exists as configured.".format(name))
            elif state == "absent":
                if module.check_mode is False:
                    response = client.security.delete_user(username=name)
                    module.exit_json(changed=True, msg="The user {0} was deleted.".format(name))
                else:
                    module.exit_json(changed=True, msg="The user {0} was deleted.".format(name))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
