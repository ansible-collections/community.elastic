#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_transform

short_description: Manage Elasticsearch Transform Jobs.

description:
  - Manage Elasticsearch user roles.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  name:
    description:
      - The name of the transform job
    type: str
    required: True
    aliases:
      - transform_id
  defer_validation:
    description:
      - When true, deferrable validations are not run.
    type: bool
    default: False
  description:
    description:
      - When true, deferrable validations are not run.
    type: str
  dest:
    description:
      - The destination for the transform.
    type: dict
    suboptions:
      index:
        description:
          - The destination index for the transform.
        type: str
        required: yes
      pipeline:
        description:
          - The unique identifier for a pipeline.
        type: str
        required: no
  frequency:
    description:
      - The interval between checks for changes in the source indices when the transform is running continuously.
      - Also determines the retry interval in the event of transient failures while the transform is searching or indexing.
    type: str
    default: "1m"
  latest:
    description:
      - The latest method transforms the data by finding the latest document for each unique key.
    type: dict
    suboptions:
      sort:
        description:
          - Specifies the date field that is used to identify the latest documents.
        type: str
      unique_key:
        description:
          - Specifies an array of one or more fields that are used to group the data.
        type: list
        elements: str
  pivot:
    description:
      - The pivot method transforms the data by aggregating and grouping it.
      - These objects define the group by fields and the aggregation to reduce the data.
    type: dict
    suboptions:
      aggregations:
        description:
          - Defines how to aggregate the grouped data.
        type: dict
        aliases:
          - "aggs"
      group_by:
        description:
          - Defines how to group the data.
          - More than one grouping can be defined per pivot.
        type: dict
        aliases:
          - "groupby"
  settings:
    description:
      - Defines optional transform settings.
    type: dict
    suboptions:
      dates_as_epoch_millis:
        description:
          - Defines if dates in the ouput should be written as ISO formatted string (default) or as millis since epoch.
        type: bool
        default: False
      docs_per_second:
        description:
          - Specifies a limit on the number of input documents per second.
        type: float
        default: null
      max_page_search_size:
        description:
          - Defines the initial page size to use for the composite aggregation for each checkpoint.
        type: int
        default: 500
  source:
    description:
      - The source of the data for the transform.
    type: dict
    suboptions:
      index:
        description:
          - The source indices for the transform.
          - It can be a single index, an index pattern (for example, "my-index-*"), \
            an array of indices (for example, ["my-index-000001", "my-index-000002"]), \
            or an array of index patterns (for example, ["my-index-*", "my-other-index-*"].
        type: raw
        required: yes
      query:
        description:
          - A query clause that retrieves a subset of data from the source index.
        type: dict
  sync:
    description:
      - Defines the properties transforms require to run continuously.
    type: dict
    suboptions:
      time:
        description:
          - Specifies that the transform uses a time field to synchronize the source and destination indices.
        type: dict
        required: yes
        suboptions:
          delay:
            description:
              - The time delay between the current time and the latest input data time.
            type: str
            default: "60s"
          field:
            description:
              - The date field that is used to identify new documents in the source.
            type: str
            required: yes
  state:
    description:
      - State of the transform job
    type: str
    choices:
      - present
      - absent
      - started
      - stopped
    default: present
'''

EXAMPLES = r'''
- name: Create a transform job with a pivot
  community.elastic.elastic_transform:
    name: ecommerce_transform1
    state: present
    source:
      index: "kibana_sample_data_ecommerce"
      query: {
          "term": {
            "geoip.continent_name": {
              "value": "Asia"
            }
          }
        }
    pivot:
      group_by: {
          "customer_id": {
            "terms": {
              "field": "customer_id"
            }
          }
        }
      aggregations: {
          "max_price": {
            "max": {
              "field": "taxful_total_price"
            }
          }
        }
    description: "Maximum priced ecommerce data by customer_id in Asia"
    dest:
      index: "kibana_sample_data_ecommerce_transform1"
      pipeline: "add_timestamp_pipeline"
    frequency: "5m"
    sync: {
        "time": {
          "field": "order_date",
          "delay": "60s"
        }
      }

- name: Delete a transform job called ecommerce_transform1
  community.elastic.elastic_transform:
    name: ecommerce_transform1
    state: absent

- name: Start a transform job called ecommerce_transform1
  community.elastic.elastic_transform:
    name: ecommerce_transform1
    state: started

- name: Stop a transform job called ecommerce_transform1
  community.elastic.elastic_transform:
    name: ecommerce_transform1
    state: stopped
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


def get_transform_job(client, name):
    '''
    Gets the transform job specified by name / job_id
    '''
    try:
        response = client.transform.get_transform(transform_id=name)
        job_config = response["transforms"][0]
    except NotFoundError:
        job_config = None
    return job_config


def get_transform_state(client, name):
    '''
    Returns the state of the transform
    '''
    try:
        response = client.transform.get_transform_stats(transform_id=name)
        job = dict(response["transforms"][0])
        if 'state' in list(job.keys()):
            state = job['state']
        else:
            state = False
    except NotFoundError:
        state = False
    return state

# TODO This will need adjusting to allow for job with some of the fields missing
# TODO Refector to a list of fields to check (dict1 & dict2)
def job_is_different(current_job, module):
    is_different = False
    if module.params['description'] != current_job['description']:
        is_different = True
    elif module.params['frequency'] != current_job['frequency']:
        is_different = True
    elif module.params['source'] != current_job['source']:
        dict1 = json.dumps(module.params['source'], sort_keys=True)
        dict2 = json.dumps(current_job['source'], sort_keys=True)
        if dict1 != dict2:
            is_different = True
    elif module.params['query'] != current_job['query']:
        dict1 = json.dumps(module.params['query'], sort_keys=True)
        dict2 = json.dumps(current_job['query'], sort_keys=True)
        if dict1 != dict2:
            is_different = True
    elif module.params['dest'] != current_job['dest']:
        dict1 = json.dumps(module.params['dest'], sort_keys=True)
        dict2 = json.dumps(current_job['dest'], sort_keys=True)
        if dict1 != dict2:
            is_different = True
    elif module.params['pivot'] != current_job['pivot']:
        dict1 = json.dumps(module.params['pivot'], sort_keys=True)
        dict2 = json.dumps(current_job['pivot'], sort_keys=True)
        if dict1 != dict2:
            is_different = True
    elif module.params['aggregations'] != current_job['aggregations']:
        dict1 = json.dumps(module.params['aggregations'], sort_keys=True)
        dict2 = json.dumps(current_job['aggregations'], sort_keys=True)
        if dict1 != dict2:
            is_different = True
    elif module.params['settings'] != current_job['settings']:
        dict1 = json.dumps(module.params['settings'], sort_keys=True)
        dict2 = json.dumps(current_job['settings'], sort_keys=True)
        if dict1 != dict2:
            is_different = True
    elif module.params['sync'] != current_job['sync']:
        dict1 = json.dumps(module.params['sync'], sort_keys=True)
        dict2 = json.dumps(current_job['sync'], sort_keys=True)
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
        "started",
        "stopped"
    ]

    argument_spec = elastic_common_argument_spec()
    # TODO Add options from above
    argument_spec.update(
        name=dict(type='str', required=True, aliases=['transform_id']),
        defer_validation=dict(type='bool', default=False),
        description=dict(type='str'),
        dest=dict(type='dict'),
        frequency=dict(type='str', default="1m"),
        latest=dict(type='dict'),
        pivot=dict(type='dict'),
        settings=dict(type='dict'),
        source=dict(type='dict'),
        sync=dict(type='dict'),
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
        check_param_state_present(module, "dest")
        check_param_state_present(module, "source")
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

        job = get_transform_job(client, name)

        # We can probably refector this code to reduce by 50% by only checking when we actually change something
        if job is not None:  # Job exists
            job_config = job
            job_status = get_transform_state(client, name)
            if module.check_mode:
                if state == "present":
                    is_different = job_is_different(job_config, module)
                    if is_different > 0:
                        module.exit_json(changed=True, msg="The transform job {0} definition was updated. {1}".format(name, is_different))
                    else:
                        module.exit_json(changed=False, msg="The transform job {0} already exists and no updates were needed.".format(name))
                elif state == "absent":
                    module.exit_json(changed=True, msg="The transform job {0} was removed.".format(name))
                elif state == "started":
                    if job_config["status"]["job_state"] == "stopped":
                        module.exit_json(changed=True, msg="The transform job {0} was started.".format(name))
                    elif job_config["status"]["job_state"] == "started":
                        module.exit_json(changed=False, msg="The transform job {0} is already in a started state".format(name))
                    else:
                        module.fail_jsob(msg="Job {0} was in a unexpected state: {1}.".format(name, state))
                elif state == "stopped":
                    if job_status["job_state"] == "started":
                        module.exit_json(changed=True, msg="The transform job {0} was stopped.".format(name))
                    elif job_status["job_state"] == "stopped":
                        module.exit_json(changed=False, msg="The transform job {0} is already in a stopped state".format(name))
                    else:
                        module.fail_jsob(msg="Job {0} was in a unexpected state: {1}.".format(name, state))
            else:
                if state == "present":
                    is_different = job_is_different(job_config, module)
                    if is_different > 0:
                        module.exit_json(changed=True, msg="The transform job {0} definition was updated. {1}".format(name, is_different))
                    else:
                        module.exit_json(changed=False, msg="The transform job {0} already exists and no updates were needed.".format(name))
                elif state == "absent":
                    response = client.transform.delete_transform(transform_id=name)
                    module.exit_json(changed=True, msg="The transform job {0} was removed.".format(name))
                elif state == "started":
                    if job_status["job_state"] == "stopped":
                        client.transform.start_transform(transform_id=name)
                        module.exit_json(changed=True, msg="The transform job {0} was started.".format(name))
                    elif job_status["job_state"] == "started":
                        module.exit_json(changed=False, msg="The transform job {0} is already in a started state".format(name))
                    else:
                        module.fail_jsob(msg="Job {0} was in a unexpected state: {1}.".format(name, state))
                elif state == "stopped":
                    if job_status["job_state"] == "started":
                        client.transform.stop_transform(transform_id=name)
                        module.exit_json(changed=True, msg="The transform job {0} was stopped.".format(name))
                    elif job_status["job_state"] == "stopped":
                        module.exit_json(changed=False, msg="The transform job {0} is already in a stopped state".format(name))
                    else:
                        module.fail_jsob(msg="Job {0} was in a unexpected state: {1}.".format(name, state))
        else:
            if module.check_mode:
                if state == "present":
                    module.exit_json(changed=True, msg="The transform job {0} was created.".format(name))
                elif state == "absent":
                    module.exit_json(changed=False, msg="The transform job {0} does not exist.".format(name))
                elif state in ["started", "stopped"]:
                    module.exit_json(changed=False, msg="Cannot stop or start a job that does not exist.")
            else:
                if state == "present":
                    body = {}
                    body_keys = [
                        "description",
                        "dest",
                        "frequency",
                        "latest",
                        "pivot",
                        "settings",
                        "source",
                        "sync"
                    ]
                    for key in body_keys:
                        body = add_if_not_none(body, key, module)
                    response = client.transform.put_transform(transform_id=name,
                                                              body=body,
                                                              headers=None,
                                                              defer_validation=module.params['defer_validation'])
                    module.exit_json(changed=True, msg="The transform job {0} was successfully created.".format(name))
                elif state == "absent":
                    module.exit_json(changed=False, msg="The transform job {0} does not exist.".format(name))
                elif state in ["started", "stopped"]:
                    module.exit_json(changed=False, msg="Cannot stop or start a job that does not exist.")

    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
