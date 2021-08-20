#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_index_info

short_description: Returns info about Elasticsearch indexes.

description:
  - Returns info about Elasticsearch indexes.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  name:
    description:
      - The index name to get information about.
    type: str
    required: True
  wait_for_active_shards:
    description:
      - A number controlling to how many active shards to wait for.
      - all to wait for all shards in the cluster to be active, or 0 to not wait.
    type: str
    default: '0'
'''

EXAMPLES = r'''
- name: Get info for myindex
  community.elastic.elastic_index_info:
    name: myindex
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

    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
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

    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        if client.indices.exists(name):
            response = dict(client.indices.get(name))
            module.exit_json(changed=False, msg="Info about index {0}.".format(name), **response)
        else:
            module.exit_json(changed=False, msg="The index {0} does not exist.".format(name))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
