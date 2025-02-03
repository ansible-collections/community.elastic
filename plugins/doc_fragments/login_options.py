from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


class ModuleDocFragment(object):
    # Standard documentation
    DOCUMENTATION = r'''
options:
  auth_method:
    description:
      - Authentication Method.
    type: str
    choices:
       - ''
       - http_auth
       - api_key
    default: ''
  auth_scheme:
    description:
      - Authentication scheme.
    type: str
    choices:
       - http
       - https
    default: http
  cafile:
    description:
      - Path to ca file
    type: str
  connection_options:
    description:
      - Additional connection options for Elasticsearch
    type: list
    elements: dict
    default: []
  login_user:
    description:
      - The Elastic user to login with.
      - Required when I(login_password) is specified.
    required: no
    type: str
  login_password:
    description:
      - The password used to authenticate with.
      - Required when I(login_user) is specified.
    required: no
    type: str
  login_hosts:
    description:
      - The Elastic hosts to connect to.
      - Can accept hostnames or URLs. If a hostname then values\
        login_port and login_scheme will be used to construct a URL.
    required: no
    type: list
    elements: str
    default: 'localhost'
  login_port:
    description:
      - The Elastic server port to login to.
    required: no
    type: int
    default: 9200
  api_key_encoded:
    description:
      - API key credentials which is the Base64-encoding of the UTF-8\
        representation of the id and api_key joined by a colon (:).
      - Supported from Elastic 8+.
      - See [Create API Key](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html) documentation for specifics.
    required: no
    type: str
  timeout:
    description:
      - Response timeout in seconds.
    type: int
    default: 30
notes:
  - Requires the elasticsearch Python module.

requirements:
  - elasticsearch
'''
