#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_cluster_health

short_description: Validate cluster health.

description:
  - Validate cluster health.
  - Optionally wait for an expected status.

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  fail_on_exception:
    description:
      - Fail immediately on exception rather than retrying.
    type: bool
    default: False
  level:
    description:
      - Controls the details level of the health information returned
    type: str
    choices:
      - cluster
      - indicies
      - shards
    default: cluster
  local:
    description:
      - If true, the request retrieves information from the local node only.
      - Defaults to false, which means information is retrieved from the master node.
    type: bool
    default: false
  poll:
    description:
      - The maximum number of times to query for the replicaset status before the set converges or we fail.
    type: int
    default: 3
  interval:
    description:
      - The number of seconds to wait between polling executions.
    type: int
    default: 10
  wait_for:
    description:
      - Wait for the specific variable to reach a specific figure.
      - Provide the name of the variable returned by cluster health API.
      - https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-health.html
    type: str
    choices:
      - null
      - number_of_nodes
      - number_of_data_nodes
      - active_primary_shards
      - active_shards
      - relocating_shards
      - initializing_shards
      - unassigned_shards
      - delayed_unassigned_shards
      - number_of_pending_tasks
      - number_of_in_flight_fetch
      - task_max_waiting_in_queue_millis
      - active_shards_percent_as_number
  to_be:
    description:
      - Used in conjunction with wait_for.
      - Expected value of the wait_for variable
    type: str
  status:
    description:
      - Expected status of the cluster changes to the one provided or better, i.e. green > yellow > red.
    type: str
    choices:
      - green
      - yellow
      - red
    default: green
'''

EXAMPLES = r'''
- name: Validate cluster health
  community.elastic.elastic_cluster_health:

- name: Ensure cluster health status is green with 90 seconds timeout
  community.elastic.elastic_cluster_health:
    wait_for_status: "green"
    timeout: 90

- name: Ensure at least 10 nodes are up with 2m timeout
  community.elastic.elastic_cluster_health:
    wait_for_nodes: ">=10"
    timeout: 2m
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
import time


def elastic_status(desired_status, cluster_status):
    '''
    Return true if the desired status is equal to or less
    than the cluster status.
    '''
    status_dict = {
        "red": 0,
        "yellow": 1,
        "green": 2
    }
    if status_dict[desired_status] <= status_dict[cluster_status]:
        return True
    else:
        return False


def cast_to_be(to_be):
    '''
    Cast the value to int if possible. Otherwise return the str value
    '''
    try:
        to_be = int(to_be)
    except ValueError:
        pass
    return to_be


# ================
# Module execution
#


def main():

    wait_for_choices = [
        None,
        'status',
        'number_of_nodes',
        'number_of_data_nodes',
        'active_primary_shards',
        'active_shards',
        'relocating_shards',
        'initializing_shards',
        'unassigned_shards',
        'delayed_unassigned_shards',
        'number_of_pending_tasks',
        'number_of_in_flight_fetch',
        'task_max_waiting_in_queue_millis',
        'active_shards_percent_as_number'
    ]

    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        level=dict(type='str', choices=['cluster', 'indicies', 'shards'], default='cluster'),
        local=dict(type='bool', default=False),
        status=dict(type='str', choices=['green', 'yellow', 'red'], default='green'),
        wait_for=dict(type='str', choices=wait_for_choices, default=None),
        to_be=dict(type='str'),
        poll=dict(type='int', default=3),
        interval=dict(type='int', default=10),
        fail_on_exception=dict(type='bool', default=False)
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False,
        required_together=[
            ['login_user', 'login_password'],
            ['wait_for', 'to_be'],
        ],
    )

    if not elastic_found:
        module.fail_json(msg=missing_required_lib('elasticsearch'),
                         exception=E_IMP_ERR)

    fail_on_exception = module.params['fail_on_exception']
    interval = module.params['interval']
    status = module.params['status']
    poll = module.params['poll']
    to_be = module.params['to_be']
    wait_for = module.params['wait_for']

    try:
        elastic = ElasticHelpers(module)
        client = elastic.connect()

        health_data = {}
        iterations = 0
        failures = 0
        temp_err = None
        msg = None
        failed = True

        while iterations < poll:
            try:
                iterations += 1
                response = client.cluster.health(level=module.params['level'],
                                                 local=module.params['local'])
                health_data = dict(response)
                if 'status' not in health_data.keys():
                    module.fail_json(msg="Elasticsearch health endpoint did not supply a status field.")
                else:
                    if elastic_status(status, health_data['status']):
                        msg = "Elasticsearch health is good."
                        if wait_for is not None:
                            if health_data[wait_for] == cast_to_be(to_be):
                                msg += " The variable {0} has reached the value {1}.".format(wait_for, to_be)
                                failed = False
                                break
                            else:
                                msg = "The variable {0} did not reached the value {1}.".format(wait_for, to_be)
                                failures += 1
                        else:
                            failed = False
                            break
                    else:
                        failures += 1

                if iterations == poll:
                    break
                else:
                    time.sleep(interval)
            except Exception as excep:
                if fail_on_exception:
                    module.fail_json(str(excep))
                failures += 1
                if iterations == poll:
                    break
                else:
                    time.sleep(interval)

        if not msg:
            msg = "Timed out waiting for elastic health to converge."

        module.exit_json(changed=False,
                         msg=msg,
                         failed=failed,
                         iterations=iterations,
                         failures=failures,
                         **health_data)

    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
