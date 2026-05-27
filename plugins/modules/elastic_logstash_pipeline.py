#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Masaru Onodera (@masa-orca)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_logstash_pipeline

short_description: Manage Logstash Pipelines in Elasticsearch.

description:
  - Manage Logstash centralized pipelines in Elasticsearch.

author: Masaru Onodera (@masa-orca)
version_added: "1.4.0"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  id:
    description:
      - The ID of the Logstash pipeline.
    type: str
    required: True
  username:
    description:
      - Username who updated the pipeline.
      - Required if state is "present".
    type: str
    required: False
  pipeline:
    description:
      - The pipeline definition.
      - Required if state is "present".
    type: str
    required: False
  description:
    description:
      - Description of the pipeline.
    type: str
    default: ""
  pipeline_metadata:
    description:
      - Metadata for the pipeline.
    type: dict
    suboptions:
      version:
        description:
          - The version of the pipeline.
        type: str
        default: "1"
      type:
        description:
          - The type of the pipeline.
        type: str
        default: "logstash_pipeline"
  last_modified:
    description:
      - The last modified time of the pipeline.
      - The time is must be in the format of I(yyyy-MM-dd'T'HH:mm:ss.SSSZZ).
      - Default is current timestamp if not specified.
    type: str
    default: ""

  pipeline_settings:
    description:
      - Settings for the pipeline.
    type: dict
    suboptions:
      pipeline_workers:
        description:
          - The number of workers for the pipeline.
        type: int
        default: 1
      pipeline_batch_size:
        description:
          - The batch size for the pipeline.
        type: int
        default: 125
      pipeline_batch_delay:
        description:
          - The batch delay for the pipeline.
        type: int
        default: 50
      queue_type:
        description:
          - The type of queue to use for the pipeline.
        type: str
        default: 'memory'
        choices:
          - memory
          - persisted
      queue_max_bytes:
        description:
          - The maximum number of bytes for the queue.
        type: str
        default: '1gb'
      queue_checkpoint_writes:
        description:
          - The number of writes for checkpointing the queue.
        type: int
        default: 1024
  state:
    description:
      - State of the pipeline.
    type: str
    choices:
      - present
      - absent
    default: present
'''

EXAMPLES = r'''
- name: Create a Logstash pipeline
  community.elastic.elastic_logstash_pipeline:
    id: my_pipeline
    username: elastic
    state: present
    description: "My centralized pipeline"
    pipeline: "{{ lookup('template', 'logstash_pipeline.conf') }}"
    pipeline_settings:
      pipeline_workers: 2
      pipeline_batch_size: 125
      pipeline_batch_delay: 5
      queue_type: 'memory'
      queue_max_bytes: 1gb
      queue_checkpoint_writes: 100
    pipeline_metadata:
      version: "1"
      type: "logstash_pipeline"
    last_modified: "2026-05-03T00:00:00.000Z"

- name: Delete a Logstash pipeline
  community.elastic.elastic_logstash_pipeline:
    id: my_pipeline
    state: absent
'''

RETURN = r'''
msg:
    description: The result of the operation
    returned: success
    type: str
    sample: "The logstash pipeline 'my_pipeline' was created."
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
from datetime import datetime, timezone


def pipeline_is_different(current_pipeline, desired_pipeline):
    is_different = False

    if desired_pipeline['description'] != current_pipeline.get('description'):
        is_different = True

    if desired_pipeline['username'] != current_pipeline.get('username'):
        is_different = True

    if desired_pipeline['pipeline'] != current_pipeline.get('pipeline'):
        is_different = True

    dict1 = json.dumps(desired_pipeline.get('pipeline_metadata') or {}, sort_keys=True)
    dict2 = json.dumps(current_pipeline.get('pipeline_metadata') or {}, sort_keys=True)
    if dict1 != dict2:
        is_different = True

    dict1 = json.dumps(desired_pipeline.get('pipeline_settings') or {}, sort_keys=True)
    dict2 = json.dumps(current_pipeline.get('pipeline_settings') or {}, sort_keys=True)
    if dict1 != dict2:
        is_different = True

    if desired_pipeline.get('last_modified') != current_pipeline.get('last_modified'):
        is_different = True

    return is_different


def main():
    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        id=dict(type='str', required=True),
        username=dict(type='str'),
        pipeline=dict(type='str'),
        description=dict(type='str', default=""),
        pipeline_metadata=dict(
            type='dict',
            options=dict(
                version=dict(type='str', default="1"),
                type=dict(type='str', default="logstash_pipeline"),
            )
        ),
        last_modified=dict(type='str', default=""),
        pipeline_settings=dict(
            type='dict',
            options={
                'pipeline_workers': dict(type='int', default=1),
                'pipeline_batch_size': dict(type='int', default=125),
                'pipeline_batch_delay': dict(type='int', default=50),
                'queue_type': dict(type='str', choices=['memory', 'persisted'], default='memory'),
                'queue_max_bytes': dict(type='str', default='1gb'),
                'queue_checkpoint_writes': dict(type='int', default=1024)
            }
        ),
        state=dict(type='str', choices=['present', 'absent'], default='present')
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[['login_user', 'login_password']],
        required_if=[
            ["state", "present", [
                "username",
                "pipeline"
            ]]
        ],
    )

    if not elastic_found:
        module.fail_json(msg=missing_required_lib('elasticsearch'),
                         exception=E_IMP_ERR)

    pipeline_id = module.params['id']
    state = module.params['state']

    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))

    logstash_pipeline_found = True
    logstash_pipeline = {}
    try:
        logstash_pipeline = client.logstash.get_pipeline(id=pipeline_id)
    except NotFoundError:
        logstash_pipeline_found = False

    try:
        if state == 'present':
            pipeline_settings = {}
            if module.params['pipeline_settings'] is not None:
                for key, value in module.params['pipeline_settings'].items():
                    pipeline_settings[key.replace('_', '.')] = value
            else:
                pipeline_settings = {
                    "pipeline.workers": 1,
                    "pipeline.batch.size": 125,
                    "pipeline.batch.delay": 50,
                    "queue.type": "memory",
                    "queue.max.bytes": "1gb",
                    "queue.checkpoint.writes": 1024
                }

            pipeline_metadata = None
            if module.params['pipeline_metadata'] is not None:
                pipeline_metadata = module.params['pipeline_metadata']
            else:
                pipeline_metadata = {
                    "version": "1",
                    "type": "logstash_pipeline"
                }

            last_modified = None
            if len(module.params['last_modified']) != 0:
                last_modified = module.params['last_modified']
            else:
                last_modified = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

            body = {
                "description": module.params['description'],
                "last_modified": last_modified,
                "username": module.params['username'],
                "pipeline": module.params['pipeline'],
                "pipeline_metadata": pipeline_metadata,
                "pipeline_settings": pipeline_settings
            }

            if logstash_pipeline_found:
                found_diff = pipeline_is_different(logstash_pipeline.get(pipeline_id), body)
                if found_diff:
                    if module.check_mode:
                        module.exit_json(changed=True, msg="The logstash pipeline '{0}' would be updated.".format(pipeline_id))
                    else:
                        client.logstash.put_pipeline(id=pipeline_id, body=body)
                        module.exit_json(changed=True, msg="The logstash pipeline '{0}' was updated.".format(pipeline_id))
                else:
                    module.exit_json(changed=False, msg="The logstash pipeline '{0}' already exists.".format(pipeline_id))
            else:
                if module.check_mode:
                    module.exit_json(changed=True, msg="The logstash pipeline '{0}' would be created.".format(pipeline_id))
                else:
                    client.logstash.put_pipeline(id=pipeline_id, body=body)
                    module.exit_json(changed=True, msg="The logstash pipeline '{0}' was created.".format(pipeline_id))
        else:
            if logstash_pipeline_found:
                if module.check_mode:
                    module.exit_json(changed=True, msg="The logstash pipeline '{0}' would be deleted.".format(pipeline_id))
                else:
                    client.logstash.delete_pipeline(id=pipeline_id)
                    module.exit_json(changed=True, msg="The logstash pipeline '{0}' was deleted.".format(pipeline_id))
            else:
                module.exit_json(changed=False, msg="The logstash pipeline '{0}' does not exist.".format(pipeline_id))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
