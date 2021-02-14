#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_reindex

short_description: Copies documents from a source to a destination.

description:
  - Copies documents from a source to a destination.
  - The source and destination can be any pre-existing index, index alias, or data stream.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  source:
    description:
      - The index to copy documents from.
    type: str
    required: True
  dest:
    description:
      - The index to copy documents to.
    type: str
    required: True
'''

EXAMPLES = r'''
- name: Copy an index
  community.elastic.elastic_reindex:
    source: myIndex1
    dest: myIndex2
'''

RETURN = r'''
msg:
  description: A short message describing what happened.
  returned: always
  type: str
task:
  description: Task id for copy job
  returned: on success when wait_for_completion is false
  type: str
changed:
  description: If something changed.
  returned: On change
  type: bool
created:
  description: Number of documents created.
  returned: on success when wait_for_completion is true
  type: int
deleted:
  description: Number of documents deleted.
  returned: on success when wait_for_completion is true
  type: int
updated:
  description: Number of documents updated.
  returned: on success when wait_for_completion is true
  type: int
failed:
  description: Number of documents failed.
  returned: on success when wait_for_completion is true
  type: int
batches:
  description: Number of batches the copy was executed in.
  returned: on success when wait_for_completion is true
  type: int
took:
  description: How long the copy took in ms.
  returned: on success when wait_for_completion is true
  type: int
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
import time


# ================
# Module execution
#


def main():

    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        source=dict(type='str', required=True),
        dest=dict(type='str', required=True),
        wait_for_completion=dict(type='bool', default=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False,
        required_together=[
            ['login_user', 'login_password']
        ],
    )

    if not elastic_found:
        module.fail_json(msg=missing_required_lib('elasticsearch'),
                         exception=E_IMP_ERR)

    source = module.params['source']
    dest = module.params['dest']
    wait_for_completion = module.params['wait_for_completion']

    try:

        elastic = ElasticHelpers(module)
        client = elastic.connect()

        result = dict(client.reindex({"source": {"index": source}, "dest": {"index": dest}}, wait_for_completion=wait_for_completion))
        if isinstance(result, dict) and 'task' in list(result.keys()):
            msg = "The copy task from {0} to {1} has been started.".format(source, dest)
            module.exit_json(changed=True,
                             msg=msg,
                             **result)
        elif isinstance(result, dict) and 'took' in list(result.keys()):
            msg = "The copy from {0} to {1} was successful.".format(source, dest)
            module.exit_json(changed=True,
                             msg=msg,
                             created=result['created'],
                             updated=result['updated'],
                             deleted=result['deleted'],
                             failed=len(result['failures']),
                             took=result['took'],
                             batches=result['batches'])
        else:
            msg = "Copy failed."
            if result is None:
                result = {}
            module.fail_json(changed=True, msg=msg, **result)

    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
