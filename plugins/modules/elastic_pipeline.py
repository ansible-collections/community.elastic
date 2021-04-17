#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_pipeline

short_description: Manage Elasticsearch Pipelines.

description:
  - Manage Elasticsearch user roles.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  name:
    description:
      - The name of the pipeline.
    type: str
    required: True
    aliases:
      - pipeline_id
  description:
    description:
      - When true, deferrable validations are not run.
    type: str
  processors:
    description:
      - Array of processors used to pre-process documents before indexing.
      - Processors are executed in the order provided.
    type: list
    elements: dict
  version:
    description:
      - Optional version number used by external systems to manage ingest pipelines.
    type: int
  state:
    description:
      - State of the pipeline
    type: str
    choices:
      - present
      - absent
    default: present
'''

EXAMPLES = r'''
- name: Create a pipeline
  community.elastic.elastic_pipeline:
    name: my-pipeline-id
    state: present
    description: "describe pipeline"
    version: 1
    processors:
      - set: {
        field: "foo",
        value: "bar"
      }

- name: Delete a pipeline
  community.elastic.elastic_pipeline:
    name: my-pipeline-id
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


def check_param_state_present(module, param):
    if module.params[param] is None:
        module.fail_json(msg="You must supply a value for {0} when state == 'present'".format(param))


def add_if_not_none(dict, key, module):
    if module.params[key] is not None:
        dict[key] = module.params[key]
    return dict


def get_pipeline(client, name):
    '''
    Gets the pipeline specified by name
    '''
    try:
        pipeline = client.ingest.get_pipeline(id=name)
        pipeline = pipeline[name]
    except NotFoundError:
        pipeline = None
    return pipeline


def pipeline_is_different(pipeline, module):
    is_different = False
    if 'description' in list(pipeline.keys()):
        if module.params['description'] != pipeline['description']:
            is_different = True
    elif 'version' in list(pipeline.keys()):
        if module.params['version'] != pipeline['version']:
            is_different = True
    elif module.params['processors'] != pipeline['processors']:
        dict1 = json.dumps(module.params['processors'], sort_keys=True)
        dict2 = json.dumps(pipeline['processors'], sort_keys=True)
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
    # TODO Add options from above
    argument_spec.update(
        name=dict(type='str', required=True, aliases=['pipeline_id']),
        description=dict(type='str'),
        processors=dict(type='list', elements='dict'),
        version=dict(type='int'),
        state=dict(type='str', choices=state_choices, default='present'),
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

    # values that should be supplied when passing state = present
    if state == 'present':
        check_param_state_present(module, "processors")
    #    check_param_state_present(module, cron, "cron")
    #    check_param_state_present(module, groups, "groups")
    #    check_param_state_present(module, metrics, "metrics")
    # Check that groups and metrics has the appropriate keys
    #    if len(set(list(groups.keys())) - set(["date_histogram", "histogram", "terms"])) > 0:
    #        module.fail_json(msg="There are invalid keys in the groups dictionary.")
    #    elif not isinstance(metrics, list):
    #        module.fail_json(msg="The metrics key does not contain a list.")

    # TODO main module logic
    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        pipeline = get_pipeline(client, name)

        # We can probably refector this code to reduce by 50% by only checking when we actually change something
        if pipeline is not None:  # pipeline exists
            if module.check_mode:
                if state == "present":
                    is_different = pipeline_is_different(pipeline, module)
                    if is_different > 0:
                        module.exit_json(changed=True, msg="The pipeline {0} definition was updated. {1}".format(name, is_different))
                    else:
                        module.exit_json(changed=False, msg="The pipeline {0} already exists and no updates were needed.".format(name))
                elif state == "absent":
                    module.exit_json(changed=True, msg="The pipeline {0} was removed.".format(name))
            else:
                if state == "present":
                    is_different = pipeline_is_different(pipeline, module)
                    if is_different > 0:
                        module.exit_json(changed=True, msg="The pipeline {0} definition was updated. {1}".format(name, is_different))
                    else:
                        module.exit_json(changed=False, msg="The pipeline {0} already exists and no updates were needed.".format(name))
                elif state == "absent":
                    response = client.ingest.delete_pipeline(id=name)
                    module.exit_json(changed=True, msg="The pipeline {0} was removed.".format(name))
        else:
            if module.check_mode:
                if state == "present":
                    module.exit_json(changed=True, msg="The pipeline {0} was successfully created.".format(name))
                elif state == "absent":
                    module.exit_json(changed=False, msg="The pipeline {0} does not exist.".format(name))
            else:
                if state == "present":
                    body = {}
                    body_keys = [
                        "description",
                        "processors",
                        "version"
                    ]
                    for key in body_keys:
                        body = add_if_not_none(body, key, module)
                    response = client.ingest.put_pipeline(id=name,
                                                          body=body,
                                                          headers=None)
                    module.exit_json(changed=True, msg="The pipeline {0} was successfully created.".format(name))
                elif state == "absent":
                    module.exit_json(changed=False, msg="The pipeline {0} does not exist.".format(name))

    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
