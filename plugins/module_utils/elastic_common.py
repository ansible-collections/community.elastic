from __future__ import absolute_import, division, print_function
__metaclass__ = type
from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible.module_utils.six.moves import configparser

import traceback
import sys

elastic_found = False
E_IMP_ERR = None
NotFoundError = None

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import NotFoundError
    elastic_found = True
except ImportError:
    E_IMP_ERR = traceback.format_exc()
    elastic_found = False


def elastic_common_argument_spec():
    """
    Returns a dict containing common options shared across the elastic modules
    """
    options = dict(
        auth_method=dict(type='str', choices=[None, 'http_auth'], default=None),
        auth_scheme=dict(type='str', choices=['http', 'https'], default='http'),
        cafile=dict(type='str', default=None),
        connection_options=dict(type='list', elements='dict', default=[]),
        login_user=dict(type='str', required=False),
        login_password=dict(type='str', required=False, no_log=True),
        login_hosts=dict(type='list', elements='str', required=False, default=['localhost']),
        login_port=dict(type='int', required=False, default=9200),
        master_timeout=dict(type='int', default=30),
        timeout=dict(type='int', default=30),
    )
    return options


class ElasticHelpers():
    """
    Class containing helper functions for Elasticsearch modules

    """
    def __init__(self, module):
        self.module = module

    def build_auth(self, module):
        '''
        Build the auth list for elastic according to the passed in parameters
        '''
        auth = {}
        if module.params['auth_method'] is not None:
            if module.params['auth_method'] == 'http_auth':
                auth["http_auth"] = (module.params['login_user'],
                                     module.params['login_password'])

                auth["http_scheme"] = module.params['auth_scheme']
                if module.params['cafile'] is not None:
                    from ssl import create_default_context
                    context = create_default_context(module.params['cafile'])
                    auth["ssl_context"] = context
            else:
                module.fail_json("Invalid or unsupported auth_method provided")
        return auth

    def connect(self):
        auth = self.build_auth(self.module)
        hosts = list(map(lambda host: "{0}:{1}".format(host,
                                                       self.module.params['login_port']),
                                                       self.module.params['login_hosts']))
        elastic = Elasticsearch(hosts,
                                master_timeout=self.module.params['master_timeout'],
                                timeout=self.module.params['timeout'],
                                *self.module.params['connection_options'],
                                **auth)
        return elastic

    def query(self, client, query):
        response = client.search(index=index, body=query)
        return response

    def index_dynamic_method(self, module, client, method, name):
        '''
        This method is here so we don't have to dulicate loads of code.
        It's only really for very simple methods where we only pass the index name
        @client - ES connection
        @method - The indicies method to call
        @name - The index name.
        '''
        if not client.indices.exists(name):
            module.fail_json(msg='Cannot perform {0} action on an index that does not exist'.format(method))
        else:
            class_method = getattr(client.indices, method)
            response = class_method(name)
            module.exit_json(changed=True, msg="The '{0}' action was performed on the index '{1}'.".format(method, name), **response)
