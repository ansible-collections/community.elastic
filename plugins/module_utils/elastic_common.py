from __future__ import absolute_import, division, print_function
__metaclass__ = type
from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible.module_utils.six.moves import configparser
from ansible.module_utils.basic import env_fallback

import traceback
import sys

elastic_found = False
E_IMP_ERR = None
NotFoundError = None
helpers = None

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import NotFoundError
    from elasticsearch import helpers
    elastic_found = True
except ImportError:
    E_IMP_ERR = traceback.format_exc()
    elastic_found = False


def elastic_common_argument_spec():
    """
    Returns a dict containing common options shared across the elastic modules
    """
    options = dict(
        auth_method=dict(type='str', choices=[None, 'http_auth'], default=None, fallback=(env_fallback, ["AUTH_METHOD"])),
        auth_scheme=dict(type='str', choices=['http', 'https'], default='http', fallback=(env_fallback, ["AUTH_SCHEME"])),
        cafile=dict(type='str', default=None, fallback=(env_fallback, ["CAFILE"])),
        connection_options=dict(type='list', elements='dict', default=[], fallback=(env_fallback, ["CONNECTION_OPTIONS"])),
        login_user=dict(type='str', required=False, fallback=(env_fallback, ["LOGIN_USER"])),
        login_password=dict(type='str', required=False, no_log=True, fallback=(env_fallback, ["LOGIN_PASSWORD"])),
        login_hosts=dict(type='list', elements='str', required=False, default=['localhost'], fallback=(env_fallback, ["LOGIN_HOSTS"])),
        login_port=dict(type='int', required=False, default=9200, fallback=(env_fallback, ["LOGIN_PORT"])),
        timeout=dict(type='int', default=30, fallback=(env_fallback, ["TIMEOUT"])),
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
        hosts = list(map(lambda host: "{0}://{1}:{2}/".format(self.module.params['auth_scheme'],
                                                              host,
                                                              self.module.params['login_port']),
                         self.module.params['login_hosts']))
        elastic = Elasticsearch(hosts,
                                timeout=self.module.params['timeout'],
                                *self.module.params['connection_options'],
                                **auth)
        return elastic

    def query(self, client, index, query):
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
        if not client.indices.exists(index=name):
            module.fail_json(msg='Cannot perform {0} action on an index that does not exist'.format(method))
        else:
            class_method = getattr(client.indices, method)
            response = class_method(name)
            module.exit_json(changed=True, msg="The '{0}' action was performed on the index '{1}'.".format(method, name), **response)
