#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_index_lifecycle

short_description: Manage Elasticsearch Index Lifecyles.

description:
  - Manage Elasticsearch Index Lifecyles.
  - Create, update and delete Index Lifecycle Polcies.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  state:
    description: The state of the ILM Policy.
    type: str
    choices:
      - present
      - absent
    default: present
  name:
    description:
      - The ILM Policy name
    type: str
    required: True
  policy:
    description:
      - The ILM Policy Document.
    type: dict
  wait_for_active_shards:
    description:
      - A number controlling to how many active shards to wait for.
      - all to wait for all shards in the cluster to be active, or 0 to not wait.
    type: str
    default: '0'
'''

EXAMPLES = r'''
- name: Create an ILM Policy
  community.elastic.elastic_index_lifecycle:
    name: mypolicy
    policy:
      phases:
        warm:
          min_age: "10d"
          actions:
            forcemerge:
              max_num_segments: 1
        delete:
          min_age: "30d"
          actions:
            delete: {}

- name: Delete an ILM Policy
  community.elastic.elastic_index:
    name: mypolicy
    state: absent
'''

RETURN = r'''
'''


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native


from ansible_collections.community.elastic.plugins.module_utils.elastic_common import (
    missing_required_lib,
    elastic_found,
    E_IMP_ERR,
    elastic_common_argument_spec,
    ElasticHelpers,
    NotFoundError
)
import json


def get_policy(client, name):
    '''
    Gets the policy document specified by name
    '''
    try:
        policy_doc = client.ilm.get_lifecycle(policy=name)[name]['policy']
    except NotFoundError:
        policy_doc = None
    return policy_doc


def lifecycle_is_different(current_policy, module):
    '''
    This document compare the phases section of the policy document only
    '''
    is_different = False
    dict1 = json.dumps(current_policy['phases'], sort_keys=True)
    dict2 = json.dumps(module.params['policy']['phases'], sort_keys=True)
    module.exit_json(msg="{0} {1}".format(str(dict1). str(dict2)))
    if dict1 != dict2:
        is_different = True
    return is_different

# ================
# Module execution
#


def main():

    state_choices = [
        "present",
        "absent",
    ]

    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
        state=dict(type='str', choices=state_choices, default='present'),
        policy=dict(type='dict', default={}),
        wait_for_active_shards=dict(type='str', default='0'),
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
    policy = module.params['policy']

    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        current_policy = get_policy(client, name)

        if module.check_mode:  # TODO implement check mode
            pass  # for absent and present we check the existence,
        else:
            if state == 'present':
                request_body = {"policy": policy}
                if current_policy is not None:
                    if lifecycle_is_different(current_policy, module):
                        response = dict(client.ilm.put_lifecycle(policy=name, body=request_body))
                        module.exit_json(changed=True, msg="The ILM Policy '{0}' was updated.".format(name), **response)
                    else:
                        module.exit_json(changed=False, msg="The ILM Policy '{0}' is configured as specified.".format(name))
                else:
                    response = dict(client.ilm.put_lifecycle(policy=name, body=request_body))
                    module.exit_json(changed=True, msg="The ILM Policy '{0}' was created.".format(name), **response)
            elif state == 'absent':
                if current_policy is not None:
                    response = dict(client.ilm.delete_lifecycle(policy=name))
                    module.exit_json(changed=True, msg="The ILM Policy '{0}' was deleted.".format(name), **response)
                else:
                    module.exit_json(changed=False, msg="The ILM Policy '{0}' does not exist.".format(name))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
