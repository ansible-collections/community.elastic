#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_bulk

short_description: Perform actions with documents using the Bulk API.

description:
  - Perform actions with documents using the Bulk API.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  actions:
    description:
      - Include json inline to insert, update or delete documents.
      - Acceptable subkeys are create, index, update & delete.
    type: dict
  src:
    description:
      - Path to a json file containing documents to bulk insert.
    type: str
  index:
    description:
      - The index to copy documents to.
    type: str
    required: True
  chunk_size:
    description:
      - Bulk insert batch size.
    type: int
    default: 1000
  stats_only:
    description:
      - Report number of successful/failed operations instead of just number of successful and a list of error responses
    type: bool
    default: True
'''

EXAMPLES = r'''
- name: Use the actions key to include json inline
  community.elastic.elastic_bulk:
    index: myindex
    actions:
      index:
        - { "quote": "To be, or not to be: that is the question" }
        - { "quote": "This above all: to thine own self be true" }
        - { "quote": "Cowards die many times before their deaths; The valiant never taste of death but once." }
        - { "_id:": 1,  "hello": "I am a document that already exists" }
      create:
        - { "foo": "bar" }
      delete:
        - { "_id": 99 }
      update:
        - { "foo": "I am a new document that will be created" }
        - { "_id": 101, "foo": "I exist already and will be updated" }

- name: Provide a file with json data
  community.elastic.elastic_bulk:
    index: myindex
    src: /path/to/data.json
'''

RETURN = r'''
  took:
    description: How long the Bulk API operation took.
    returned: on success
    type: int
  errors:
    description: Number of Bulk errors,
    returned: on success
    type: int
  error_docs:
    description: Array of documents that failed
    returned: when stats_only is False
    type: dict
'''


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native


from ansible_collections.community.elastic.plugins.module_utils.elastic_common import (
    missing_required_lib,
    elastic_found,
    E_IMP_ERR,
    elastic_common_argument_spec,
    ElasticHelpers,
    helpers
)
import time
import json
import uuid


def process_document_for_bulk(module, index, action, document):
    '''
    Processes documents into a format suitable for the Elastic Bulk API
    '''
    _id = document.pop('_id', None)
    if action == 'delete' and _id is None:
        module.fail_json(msg="An _id value must be supplied when deleting documents")
    bulk_doc = {
        '_op_type': action,
        '_index': index,
        '_type': '_doc'
    }
    if _id is not None:
        bulk_doc['_id'] = _id
    if action == 'update':
        bulk_doc['doc'] = document
    elif action in ['create', 'index']:
        bulk_doc.update(document)
    return bulk_doc


def get_data_from_file(file_name):
    file = open(file_name, encoding="utf8", errors='ignore')
    data = [line.strip() for line in file]
    file.close()
    return data


def bulk_json_data(json_file, _index, doc_type):
    '''
    generator to push bulk data from a JSON
    file into an Elasticsearch index
    https://kb.objectrocket.com/elasticsearch/how-to-use-python-helpers-to-bulk-load-data-into-an-elasticsearch-index
    '''
    json_list = get_data_from_file(json_file)
    for doc in json_list:
        # use a `yield` generator so that the data
        # isn't loaded into memory

        if '{"index"' not in doc:
            yield {
                "_index": _index,
                "_type": doc_type,
                "_id": uuid.uuid4(),
                "_source": doc
            }


# ================
# Module execution
#


def main():

    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        src=dict(type='str'),
        actions=dict(type='dict'),
        chunk_size=dict(type='int', default=1000),
        index=dict(type='str', required=True),
        stats_only=dict(type='bool', default=True),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[
            ['login_user', 'login_password']
        ],
    )

    if not elastic_found:
        module.fail_json(msg=missing_required_lib('elasticsearch'),
                         exception=E_IMP_ERR)

    index = module.params['index']
    src = module.params['src']
    actions = module.params['actions']
    chunk_size = module.params['chunk_size']
    stats_only = module.params['stats_only']

    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        bulk_actions = []

        if actions is not None:  # Build actions iterable
            if len(list(set(actions.keys()) - set(["create", "index", "update", "delete"]))) > 0:
                module.fail_json(msg="Invalid key provided in actions dictionary")
            else:  # https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-bulk.html
                if "create" in list(actions.keys()):
                    if isinstance(actions['create'], list):
                        for item in actions['create']:
                            bulk_actions.append(process_document_for_bulk(module,
                                                                          index,
                                                                          'create',
                                                                          item))
                    else:
                        module.fail_json(msg="create key should be a list")
                if "index" in list(actions.keys()):
                    if isinstance(actions['index'], list):
                        for item in actions['index']:
                            bulk_actions.append(process_document_for_bulk(module,
                                                                          index,
                                                                          'index',
                                                                          item))
                    else:
                        module.fail_json(msg="index key should be a list")
                if "update" in list(actions.keys()):
                    if isinstance(actions['update'], list):
                        for item in actions['update']:
                            bulk_actions.append(process_document_for_bulk(module,
                                                                          index,
                                                                          'update',
                                                                          item))
                    else:
                        module.fail_json(msg="update key should be a list")
                if "delete" in list(actions.keys()):
                    if isinstance(actions['delete'], list):
                        for item in actions['delete']:
                            bulk_actions.append(process_document_for_bulk(module,
                                                                          index,
                                                                          'delete',
                                                                          item))
                    else:
                        module.fail_json(msg="delete key should be a list")
        elif src is not None:
            bulk_actions = bulk_json_data(src, index, "document")
        else:
            module.fail_json(msg="Must supply one of actions or src when executing this module.")

        response = helpers.bulk(client,
                                bulk_actions,
                                index=index,
                                chunk_size=chunk_size,
                                stats_only=stats_only)

        took, errors = response

        response_dict = {}

        if stats_only:
            response_dict['took'] = took
            response_dict['errors'] = errors
        else:
            response_dict['took'] = took
            response_dict['errors'] = len(errors)
            response_dict['error_docs'] = errors

        module.exit_json(changed=True, msg="Successfully executed Bulk actions", **response_dict)

    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
