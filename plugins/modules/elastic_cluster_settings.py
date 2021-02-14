#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: elastic_cluster_settings

short_description: Manage Elastic Search Cluster Settings

description:
  - Manage Elastic Search Cluster Settings

author: Rhys Campbell (@rhysmeister)
version_added: "0.0.1"

extends_documentation_fragment:
  - community.elastic.login_options

options:
  persistent:
    description:
      - Whether to make a setting update persistent or transient.
      - If security is enabled you need the manage cluster privilege.
    type: bool
    default: true
  settings:
    description:
      - The Elastic search settings to update.
      - Supply as a dict key/values.
    type: dict
'''

EXAMPLES = r'''
- name: Update a setting
  community.elastic.elastic_cluster
    settings:
      - "indices.recovery.max_bytes_per_sec": "50mb"

- name: Reset a bunch of settings to their default value
  community.elastic.elastic_cluster_settings:
    settings:
      action.auto_create_index: null
      action.destructive_requires_name: null
      cluster.auto_shrink_voting_configuration: null
      cluster.indices.close.enable: null
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


def cluster_put_settings(client, body):
    response = client.cluster.put_settings(body=body, params=None, headers=None)
    return response


def cluster_get_settings(client):
    response = client.cluster.get_settings(include_defaults=True,
                                           flat_settings=True)
    return response


# ================
# Module execution
#

def main():
    argument_spec = elastic_common_argument_spec()
    argument_spec.update(
        persistent=dict(type='bool', default=True),
        settings=dict(type='dict', required=True),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[['login_user', 'login_password']],
    )

    if not elastic_found:
        module.fail_json(msg=missing_required_lib('elasticsearch'),
                         exception=E_IMP_ERR)

    persistent = module.params['persistent']
    settings = module.params['settings']

    # TODO main module logic
    try:
        if persistent:
            settings_doc = {"persistent": settings}
        else:
            settings_doc = {"transient": settings}

        elastic = ElasticHelpers(module)
        client = elastic.connect()

        current_settings = cluster_get_settings(client)

        if persistent:
            del current_settings['transient']
        else:
            del current_settings['persistent']

        # Fail if we have any unexpected keys
        if len(list(set(current_settings.keys()) - set(['persistent', 'transient', 'defaults']))) > 0:
            unexpected_keys = list(set(current_settings.keys()) - set(['persistent', 'transient', 'defaults']))
            module.fail_json(msg="Unexpected key found in cluster config: {0}".format(str(unexpected_keys)))

        cluster_configuration_changes = {}
        selected_key = list(settings_doc.keys())[0]
        none_debug = False
        for config_item in list(settings_doc[selected_key].keys()):
            desired_value = None
            actual_value = None
            if settings_doc[selected_key][config_item] is None \
                    and config_item in list(current_settings[selected_key].keys()):
                cluster_configuration_changes[config_item] = {
                    "old_value": None,
                    "new_value": "<default>"
                }
            elif settings_doc[selected_key][config_item] == \
                    current_settings[selected_key].get(config_item):
                pass
            elif settings_doc[selected_key][config_item] == \
                    current_settings["defaults"].get(config_item):
                pass
            else:
                # If we reach here the value results in a cluster settings change
                desired_value = settings_doc[selected_key][config_item]
                actual_value = current_settings[selected_key].get(config_item)
                if actual_value is None:
                    actual_value = current_settings["defaults"].get(config_item)
                cluster_configuration_changes[config_item] = {
                    "old_value": actual_value,
                    "new_value": desired_value
                }

        if none_debug:
            module.exit_json(**cluster_configuration_changes)

        if cluster_configuration_changes == {}:
            module.exit_json(changed=False, msg="There are no cluster configuration changes to perform.")
        else:
            if module.check_mode:
                module.exit_json(changed=True,
                                 msg="The cluster configuration has been updated.",
                                 cluster_cfg_changes=cluster_configuration_changes)
            else:
                response = cluster_put_settings(client, body=settings_doc)
                if response['acknowledged']:
                    module.exit_json(changed=True,
                                     msg="The cluster configuration has been updated.",
                                     cluster_cfg_changes=cluster_configuration_changes)
                else:
                    module.fail_json(msg="Something has gone wrong: {0}".format(str(response)))
    except Exception as excep:
        module.fail_json(msg='Elastic error: %s' % to_native(excep))


if __name__ == '__main__':
    main()
