#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Rhys Campbell (@rhysmeister) <rhyscampbell@bluewin.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_api_key

short_description: Create and manage API keys for elastic.

description:
  - Create and manage API keys for elastic.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  name:
    description:
      - The name of the API key.
    type: str
    required: true
  state:
    description:
      - The required state of the API key.
    type: str
    choices:
      - present
      - absent
    default: present
  expiration:
    description:
      - The expiration time for the API key. 
      - By default, API keys never expire.
    type: str
    defaule: none
  role_descriptors:
    description:
      - An array of role descriptors for this API key. 
      - When it is not specified or it is an empty array, the API key will have a point in time snapshot of permissions of the authenticated user.
    type: dict
  metadata:
    description:
      - Arbitrary metadata that you want to associate with the API key. 
      - It supports nested data structure.
    type: dict
'''

EXAMPLES = r'''
- name: Create an api key
  community.elastic.elastic_api_key:
    name: myAPIKey

- name: Delete an api key
  community.elastic.elastic_api_key:
    name: myAPIKey
    state: absent

- name: Create an api key with custom permissions
  community.elastic.elastic_api_key:
    name: myAPIKey
    state: present
    expiration: 7d
    role_descriptors:
      "role-a":
        cluster:
          - all
        indicies:
          - name: "index-a*"
            privileges:
              - read
      "role-b":
        cluster:
          - all
        indicies:
          - name: "index-b*"
          privileges:
            - all


'''

RETURN = r'''
  api_key:
    description: Generated API key.
    returned: on success
    type: str
  expiration:
    description: Expiration in milliseconds for the API key.
    returned: on success
    type: int
  id:
    description: Unique ID for this API key.
    returned: on success
    type: str
  name:
    description: Specifies the name for this API key.
    returned: on success
    type: str
  encoded:
    description: API key credentials which is the base64-encoding of the UTF-8 representation of id and api_key joined by a colon (:).
    returned: on success
    type: str       
'''


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

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

def api_key_exists(client, name):
    """
    Checks if an api key with the given name exists
    """
    resp = client.security.query_api_keys(
        query={
            "match": {
                "name": name
            }
        }
    )
    return len(resp.get("api_keys", [])) > 0

def create_api_key(module, client):
    """
    Creates an Elastic api key
    """
    name = module.params['name']
    role_descriptors = module.params['role_descriptors']
    metadata = module.params['metadata']
    expiration = module.params['expiration']
    resp = client.security.create_api_key(
        name=name,
        role_descriptors=role_descriptors,
        metadata=metadata,
        expiration=expiration
    )
    return resp

def delete_api_key(client, name):
    """
    We cannot directly delete an api key, we invalidate it and then, at some point, elastic will clean it up
    """
    resp = client.security.invalidate_api_key(
        name=name
    )
    return resp

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
        name=dict(type='str', required=True),
        state=dict(type='str', choices=state_choices, default='present'),
        expiration=dict(type='int', default=None),
        role_descriptors=dict(type='dict', default={}),
        metadata=dict(type='dict', default={}),
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

        api_key = api_key_exists(client, name) 
        

        if api_key is False:
            if state == "present":
                if module.check_mode is False:
                    response = create_api_key(module, client)
                module.exit_json(changed=True, msg="The api key {0} was successfully created: {1}".format(name, str(response)))
            elif state == "absent":
                module.exit_json(changed=False, msg="The api key {0} does not exist.".format(name))
        else:  # api key already exists, we don't update anything
            if state == "present":
                module.exit_json(changed=False, msg="The api key {0} already exists.".format(name))
            elif state == "absent":
                if module.check_mode is False:
                    delete_api_key(client, name)
                    module.exit_json(changed=True, msg="The api key {0} was deleted.".format(name))
                else:
                    module.exit_json(changed=True, msg="The api key {0} was deleted.".format(name))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
