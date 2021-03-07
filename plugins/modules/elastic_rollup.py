#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_rollup

short_description: Manage Elasticsearch Rollup Jobs.

description:
  - Manage Elasticsearch Rollup Jobs.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  name:
    description:
      - The name of the rollup job
    type: str
    required: True
  index_pattern:
    description:
      - The index pattern to roll up.
    type: str
  rollup_index:
    description:
      - The index that contains the rollup results.
    type: str
  cron:
    description:
      - A cron string which defines the intervals when the rollup job should be executed.
    type: str
  page_size:
    description:
      - The number of bucket results that are processed on each iteration of the rollup indexer.
    type: int
    default: 1000
  groups:
    description:
      - Defines the grouping fields and aggregations that are defined for this rollup job.
    type: dict
    suboptions:
      date_histogram:
        description:
          - A date histogram group aggregates a date field into time-based buckets.
        type: dict
        required: True
      histogram:
        description:
          - The histogram group aggregates one or more numeric fields into numeric histogram intervals.
        type: dict
      terms:
        description:
          - The terms group can be used on keyword or numeric fields to allow bucketing via the terms aggregation at a later point.
        type: dict
  metrics:
    description:
      - Defines the metrics to collect for each grouping tuple.
    type: list
    elements: dict
    suboptions:
      field:
        description:
          - The field to collect metrics for. This must be a numeric of some kind.
        type: str
        required: True
      metric:
        description:
          - An array of metrics to collect for the field.
          - At least one metric must be configured.
          - Acceptable metrics are min,max,sum,avg, and value_count.
        type: list
        elements: str
  state:
    description:
      - State of the rollup job
    type: str
    choices:
      - present
      - absent
      - started
      - stopped
    default: present
'''

EXAMPLES = r'''
- name: Create a roll up job called sensor
  community.elastic.elastic_rollup:
    name: sensor
    state: present
    index_pattern: "sensor-*"
    rollup_index: "sensor_rollup"
    cron: "*/30 * * * * ?"
    page_size: 1000
    groups:
      date_histogram:
        field: "timestamp"
        fixed_interval: "1h"
        delay: "7d"
      terms:
        fields:
          - "node"
    metrics:
      - field: "temperature"
        metrics:
          - "min"
          - "max"
          - "sum"
      - field: "voltage"
        metrics:
          - "avg"

- name: Delete a roll up job called sensor
  community.elastic.elastic_rollup:
    name: sensor
    state: absent

- name: Start a roll up job called sensor
  community.elastic.elastic_rollup:
    name: sensor
    state: started

- name: Stop a roll up job called sensor
  community.elastic.elastic_rollup:
    name: sensor
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
    ElasticHelpers
)
import json


def check_param_state_present(module, param, param_name):
    if param is None:
        module.fail_json(msg="You must supply a value for {0} when state == 'present'".format(param_name))


def get_rollup_job(client, name):
    '''
    Gets the rollup job specified by name / job_id
    '''
    response = client.rollup.get_jobs(id=name)
    try:
        job_config = response["jobs"][0]
    except IndexError:
        job_config = None
    return job_config


# TODO Seems solid refactor to True / False
def job_is_different(current_job, module):
    is_different = 0
    if module.params['index_pattern'] != current_job['index_pattern']:
        is_different += 1
    elif module.params['rollup_index'] != current_job['rollup_index']:
        is_different += 2
    elif module.params['cron'] != current_job['cron']:
        is_different += 4
    elif module.params['groups'] != current_job['groups']:
        dict1 = json.dumps(module.params['groups'], sort_keys=True)
        dict2 = json.dumps(current_job['groups'], sort_keys=True)
        if dict1 != dict2:
            is_different += 8
    elif module.params['metrics'] != current_job['metrics']:
        dict1 = json.dumps(module.params['metrics'], sort_keys=True)
        dict2 = json.dumps(current_job['metrics'], sort_keys=True)
        if dict1 != dict2:
            is_different += 8  # todo need timeout here? How to avoid clash with the general timeout var?
    elif module.params['page_size'] != current_job['page_size']:
        is_different += 32
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
        name=dict(type='str', required=True),
        index_pattern=dict(type='str'),
        rollup_index=dict(type='str'),
        cron=dict(type='str'),
        page_size=dict(type='int', default=1000),
        groups=dict(type='dict'),
        metrics=dict(type='list', elements='dict'),
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
    index_pattern = module.params['index_pattern']
    rollup_index = module.params['rollup_index']
    cron = module.params['cron']
    page_size = module.params['page_size']
    groups = module.params['groups']
    metrics = module.params['metrics']
    state = module.params['state']

    # values that should be supplied when passing state = present
    if state == 'present':
        check_param_state_present(module, index_pattern, "index_pattern")
        check_param_state_present(module, rollup_index, "rollup_index")
        check_param_state_present(module, cron, "cron")
        check_param_state_present(module, groups, "groups")
        check_param_state_present(module, metrics, "metrics")
        # Check that groups and metrics has the appropriate keys
        if len(set(list(groups.keys())) - set(["date_histogram", "histogram", "terms"])) > 0:
            module.fail_json(msg="There are invalid keys in the groups dictionary.")
        elif not isinstance(metrics, list):
            module.fail_json(msg="The metrics key does not contain a list.")

    # TODO main module logic
    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        job = get_rollup_job(client, name)

        # We can probably refector this code to reduce by 50% by only chekcing check ode when we actually change something
        if job is not None:  # Job exists
            job_config = job['config']
            job_status = job['status']
            if module.check_mode:
                if state == "present":
                    is_different = job_is_different(job_config, module)
                    if is_different > 0:
                        module.exit_json(changed=True, msg="The rollup job {0} definition was updated. {1}".format(name, is_different))
                    else:
                        module.exit_json(changed=False, msg="The rollup job {0} already exists and no updates were needed.".format(name))
                elif state == "absent":
                    module.exit_json(changed=True, msg="The rollup job {0} was removed.".format(name))
                elif state == "started":
                    if job_config["status"]["job_state"] == "stopped":
                        module.exit_json(changed=True, msg="The rollup job {0} was started.".format(name))
                    elif job_config["status"]["job_state"] == "started":
                        module.exit_json(changed=False, msg="The rollup job {0} is already in a started state".format(name))
                    else:
                        module.fail_jsob(msg="Job {0} was in a unexpected state: {1}.".format(name, state))
                elif state == "stopped":
                    if job_status["job_state"] == "started":
                        module.exit_json(changed=True, msg="The rollup job {0} was stopped.".format(name))
                    elif job_status["job_state"] == "stopped":
                        module.exit_json(changed=False, msg="The rollup job {0} is already in a stopped state".format(name))
                    else:
                        module.fail_jsob(msg="Job {0} was in a unexpected state: {1}.".format(name, state))
            else:
                if state == "present":
                    is_different = job_is_different(job_config, module)
                    if is_different > 0:
                        module.exit_json(changed=True, msg="The rollup job {0} definition was updated. {1}".format(name, is_different))
                    else:
                        module.exit_json(changed=False, msg="The rollup job {0} already exists and no updates were needed.".format(name))
                elif state == "absent":
                    response = client.rollup.delete_job(id=name)
                    module.exit_json(changed=True, msg="The rollup job {0} was removed.".format(name))
                elif state == "started":
                    if job_status["job_state"] == "stopped":
                        client.rollup.start_job(name)
                        module.exit_json(changed=True, msg="The rollup job {0} was started.".format(name))
                    elif job_status["job_state"] == "started":
                        module.exit_json(changed=False, msg="The rollup job {0} is already in a started state".format(name))
                    else:
                        module.fail_jsob(msg="Job {0} was in a unexpected state: {1}.".format(name, state))
                elif state == "stopped":
                    if job_status["job_state"] == "started":
                        client.rollup.stop_job(name)
                        module.exit_json(changed=True, msg="The rollup job {0} was stopped.".format(name))
                    elif job_status["job_state"] == "stopped":
                        module.exit_json(changed=False, msg="The rollup job {0} is already in a stopped state".format(name))
                    else:
                        module.fail_jsob(msg="Job {0} was in a unexpected state: {1}.".format(name, state))
        else:
            if module.check_mode:
                if state == "present":
                    module.exit_json(changed=True, msg="The rollup job {0} was created.".format(name))
                elif state == "absent":
                    module.exit_json(changed=False, msg="The rollup job {0} does not exist.".format(name))
                elif state in ["started", "stopped"]:
                    module.exit_json(changed=False, msg="Cannot stop or start a job that does not exist.")
            else:
                if state == "present":
                    body = {
                        "cron": cron,
                        "groups": groups,
                        "index_pattern": index_pattern,
                        "metrics": metrics,
                        "page_size": page_size,
                        "rollup_index": rollup_index
                    }
                    response = client.rollup.put_job(id=name,
                                                     body=body,
                                                     headers=None)
                    module.exit_json(changed=True, msg="The rollup job {0} was successfully created.".format(name))
                elif state == "absent":
                    module.exit_json(changed=False, msg="The rollup job {0} does not exist.".format(name))
                elif state in ["started", "stopped"]:
                    module.exit_json(changed=False, msg="Cannot stop or start a job that does not exist.")

    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
