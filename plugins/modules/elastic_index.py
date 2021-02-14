#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_index

short_description: Manage Elasticsearch indexes.

description:
  - Manage Elasticsearch indexes.
  - Create indexes and drop indexes.
  - Perform some index maintenance operations.
  - Create indexes with settings and mapping documents.
  - No support for settings or mapping document updates.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  state:
    description: The state of the index.
    type: str
    choices:
      - present
      - absent
      - closed
      - opened
      - clear_cache
      - flush
      - flush_synced
      - info
      - refresh
      - stats
      - upgrade
    default: present
  name:
    description:
      - The index name
    type: str
    required: yes
  settings:
    description:
      - Index settings document.
    type: dict
    required: no
  mappings:
    description:
      - Index mappings document.
    type: dict
    required: no
  wait_for_active_shards:
    description:
      - A number controlling to how many active shards to wait for.
      - all to wait for all shards in the cluster to be active, or 0 to not wait.
    type: str
    default: '0'
'''

EXAMPLES = r'''
- name: Create an index called myindex
  community.elastic.elastic_index:
    name: myindex

- name: Delete an index called myindex
  community.elastic.elastic_index:
    name: myindex
    state: absent

- name: Close an index called myindex
  community.elastic.elastic_index:
    name: myindex
    state: closed

- name: Create an index called myindex with some settings and mappings
  community.elastic.elastic_index:
    name: myindex
    settings:
      number_of_shards: 5
      number_of_replicas: 3
    mappings:
      properties:
        age: { "type": "integer" }
        email: { "type": "keyword" }
        name: { "type": "text" }
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
    ElasticHelpers
)


# ================
# Module execution
#

def main():

    state_choices = [
        "present",
        "absent",
        "closed",
        "opened",
        "clear_cache",
        "flush",
        "flush_synced",
        "info",
        "refresh",
        "stats",
        "upgrade"
    ]

    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        name=dict(type='str', required='yes'),
        state=dict(type='str', choices=state_choices, default='present'),
        settings=dict(type='dict', default={}),
        mappings=dict(type='dict', default={}),
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
    settings = module.params['settings']
    mappings = module.params['mappings']
    state = module.params['state']

    # TODO main module logic
    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        if module.check_mode:
            pass  # for absent and present we check the existence, other states just return always changed
        else:
            if state == 'present':
                if client.indices.exists(name):
                    module.exit_json(changed=False, msg="The index '{0}' already exists.".format(name))
                else:
                    request_body = {"settings": settings, "mappings": mappings}
                    response = dict(client.indices.create(index=name, body=request_body))
                    module.exit_json(changed=True, msg="The index '{0}' was created.".format(name), **response)
            elif state == 'absent':
                if client.indices.exists(name):
                    response = dict(client.indices.delete(name))
                    module.exit_json(changed=True, msg="The index '{0}' was deleted.".format(name), **response)
                else:
                    module.exit_json(changed=False, msg="The index '{0}' does not exist.".format(name))
            elif state == "closed":
                elastic.index_dynamic_method(module, client, 'close', name)
            elif state == "opened":
                elastic.index_dynamic_method(module, client, 'open', name)
            elif state == "upgrade":
                elastic.index_dynamic_method(module, client, 'upgrade', name)
            elif state == "info":
                response = dict(client.indices.get(name))
                module.exit_json(changed=True, msg="Info about index '{0}'.".format(name), **response)
            elif state == "stats":
                response = dict(client.indices.stats(name))
                module.exit_json(changed=True, msg="Stats from index '{0}'.".format(name), **response)
            else:  # Catch all for everything else. Need to make sure the state == method name
                elastic.index_dynamic_method(module, client, state, name)
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
