#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2022, J. M. Becker (@techzilla)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
from pprint import pformat
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_index_lifecycle

short_description: Manage Elasticsearch Index Templates.

description:
  - Manage Elasticsearch Index Templates.
  - Create, update and delete Index Templates

author: J. M. Becker (@techzilla)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  state:
    description: The state of the Index Template.
    type: str
    choices:
      - present
      - absent
    default: present
  name:
    description:
      - The Index Template name
    type: str
    required: True
  template:
    description:
      - The Index Template Document.
    type: dict
  wait_for_active_shards:
    description:
      - A number controlling to how many active shards to wait for.
      - all to wait for all shards in the cluster to be active, or 0 to not wait.
    type: str
    default: '0'
'''

EXAMPLES = r'''
- name: Create an Index Template
  community.elastic.elastic_index_template:
    name: mytemplate
    template:
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

- name: Delete an Index Template
  community.elastic.elastic_index:
    name: mytemplate
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


def convert_values_to_int(d):
    for k,v in d.items():
        if type(v) == dict:
            convert_values_to_int(v)
        elif type(v) == str and v.isdigit():
            d[k] = int(v)
    return d

def is_index_template_different(current_template, new_template):

  current_template_cast=convert_values_to_int(current_template)
  new_template_cast=convert_values_to_int(new_template)

  for t1 in new_template_cast:
    if new_template_cast[t1] is not None:
      if new_template_cast[t1] != current_template_cast[t1]:
        return True
  return False

def get_index_template(client, name):
    '''
    Gets the Template document specified by name
    '''
    try:
        template_doc = client.indices.get_index_template(name=name)["index_templates"][0]["index_template"]
    except NotFoundError:
        template_doc = None
    return template_doc



def main():

    state_choices = [
        "present",
        "absent",
    ]

    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
        state=dict(type='str', choices=state_choices, default='present'),
        index_patterns=dict(type='list', elements='str'),
        data_stream=dict(type='dict'),
        template=dict(type='dict', default={}),
        composed_of=dict(type='list', elements='str'),
        priority=dict(type='int'),
        version=dict(type='int'),
        meta=dict(type='dict', default={})
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
    template = module.params['template']
    index_patterns = module.params['index_patterns']
    data_stream = module.params['data_stream']
    template = module.params['template']
    composed_of = module.params['composed_of']
    priority = module.params['priority']
    version = module.params['version']
    meta = module.params['meta']

    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        current_template = get_index_template(client, name)

        # module.exit_json(msg=current_template)
        # client.indices.get_index_template(name=name)


        if state == 'present':
            request_body = {
                            "index_patterns": index_patterns,
                            "composed_of": composed_of,
                            "template": template,
                            "data_stream": data_stream,
                            "priority": priority,
                            "meta": meta,
                            "version": version
                            }
            if current_template is not None:

                new_template = {
                            "index_patterns": index_patterns,
                            "composed_of": composed_of,
                            "template": template,
                            "data_stream": data_stream,
                            "priority": priority,
                            "_meta": meta,
                            "version": version
                            }
                # module.exit_json(msg=convert_values_to_int(current_template))
                if (is_index_template_different(current_template, new_template )):
                  response = dict(client.indices.put_index_template(name=name, **request_body))
                  module.exit_json(changed=True, msg="The index template '{0}' was created.".format(name), **response)
                else:
                  module.exit_json(changed=False, msg="The index template '{0}' already exists.".format(name))
            else:
                response = dict(client.indices.put_index_template(name=name, **request_body))
                module.exit_json(changed=True, msg="The index template '{0}' was created.".format(name), **response)



        elif state == 'absent':
            if current_template is not None:
                if module.check_mode:
                    response = {"acknowledged": True}
                else:
                    response = dict(client.indices.delete_index_template(name=name))
                module.exit_json(changed=True, msg="The index template '{0}' was deleted.".format(name), **response)
            else:
                module.exit_json(changed=False, msg="The index template '{0}' does not exist.".format(name))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
