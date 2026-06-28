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
  - To protect sensitive value you can use no_log with this module.

author: Rhys Campbell (@rhysmeister)
version_added: "1.4.0"

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
      - It is not possible to hard delete a \
        api key, so they are expired, Elastic \
        will clean them up at some point.
      - This means that you will encounter problems \
        when attempting to quicky delete and recreate \
        api keys with the same name.
      - Api Keys cannot be updated after creation via this module.
    type: str
    choices:
      - present
      - absent
    default: present
  expiration:
    description:
      - The expiration time for the API key.
      - By default, API keys never expire.
      - Accepts various time units e.g. 7d, 1M, 24h.
    type: str
    default: null
  role_descriptors:
    description:
      - An array of role descriptors for this API key.
      - When it is not specified or it is an empty array, the API key will have a point in time snapshot of permissions of the authenticated user.
    type: dict
    default: {}
  metadata:
    description:
      - Arbitrary metadata that you want to associate with the API key.
      - It supports nested data structure.
    type: dict
    default: {}
'''

EXAMPLES = r'''
- name: Create an api key
  community.elastic.elastic_api_key:
    name: myAPIKey
  no_log: true

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
        indices:
          - names:
            - "index-a*"
            privileges:
              - read
      "role-b":
        cluster:
          - all
        indices:
          - names:
            - "index-b*"
            privileges:
              - all
  no_log: true
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
try:
    import elasticsearch
except ImportError:
    pass
import time

from ansible_collections.community.elastic.plugins.module_utils.elastic_common import (
    missing_required_lib,
    elastic_found,
    E_IMP_ERR,
    elastic_common_argument_spec,
    ElasticHelpers
)


def api_key_exists_expired(client, name):
    """
    Checks if an API key with the given name exists and is NOT expired.

    Returns:
        True  -> at least one valid (non-expired, non-invalidated) key exists
        False -> no key exists OR all keys are expired/invalidated
    """

    resp = client.security.query_api_keys(
        body={
            "query": {
                "term": {
                    "name": name
                }
            }
        }
    )

    api_keys = resp.get("api_keys", [])

    if not api_keys:
        return False

    now = int(time.time() * 1000)

    for key in api_keys:
        if key.get("invalidated", False):
            continue
        expiration = key.get("expiration")
        if expiration is None or expiration > now:
            return True
    return False


def create_api_key(module, client):
    """
    Creates an Elastic API key (compatible with ES 7 and 8+)
    """
    name = module.params['name']
    role_descriptors = module.params.get('role_descriptors')
    metadata = module.params.get('metadata')
    expiration = module.params.get('expiration')

    version = elasticsearch.VERSION
    major = version[0]

    # Build payload once
    payload = {
        "name": name
    }

    if role_descriptors is not None:
        payload["role_descriptors"] = role_descriptors
    if metadata is not None:
        payload["metadata"] = metadata
    if expiration is not None:
        payload["expiration"] = expiration

    if major <= 7:
        # ES 7.x requires body=
        resp = client.security.create_api_key(body=payload)
    else:
        # ES 8+ uses keyword arguments
        resp = client.security.create_api_key(**payload)

    return resp


def delete_api_key(client, name):
    """
    Invalidates an API key by name (ES 7 and 8+ compatible)
    """
    version = elasticsearch.VERSION
    major = version[0]

    if major <= 7:
        # ES 7.x: must use body
        resp = client.security.invalidate_api_key(
            body={
                "name": name
            }
        )
    else:
        # ES 8+: keyword arguments
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
        expiration=dict(type='str', default=None),
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

        api_key = api_key_exists_expired(client, name)

        if api_key is False:
            if state == "present":
                if module.check_mode is False:
                    response = create_api_key(module, client)
                module.exit_json(
                    changed=True,
                    msg="The api key {0} was successfully created.".format(name),
                    **response
                )
            elif state == "absent":
                module.exit_json(changed=False, msg="The api key {0} does not exist or is expired.".format(name))
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
