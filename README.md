# community.elastic

![CI](https://github.com/ansible-collections/community.elastic/workflows/CI/badge.svg)
![Build & Publish Collection](https://github.com/ansible-collections/community.elastic/workflows/Build%20&%20Publish%20Collection/badge.svg)

This Ansible collection provides modules to work with Elasticsearch instances and clusters.

## Installing the official release

Not yet available.

~~ansible-galaxy colleciton install community.elastic~~

# Installing the latest development version

At the moment please ensure you are using version 7 of the elasticsearch driver. [8+ is not currently supported](https://github.com/ansible-collections/community.elastic/issues/58).

```bash
pip install elasticsearch==7.*
```

```bash
ansible-galaxy collection install https://github.com/ansible-collections/community.elastic/releases/download/latest/community-elastic-latest.tar.gz
```

## Collection Contents

These modules are tested on Debian and RHEL based distributions.

### Modules

- `elastic_bulk`: Perform actions with documents using the Bulk API.
- `elastic_cluster_health`: Validate cluster health.
- `elastic_cluster_settings`: Manage Elastic Search Cluster Settings.
- `elastic_index`:  Manage Elasticsearch indexes.
- `elastic_index_info`: Returns info about Elasticsearch indexes.
- `elastic_index_lifecycle`: Manage Elasticsearch Index Lifecyles.
- `elastic_pipeline`: Manage Elasticsearch Pipelines.
- `elastic_reindex`: Copies documents from a source to a destination.
- `elastic_role`: Manage Elasticsearch user roles.
- `elastic_rollup`: Manage Elasticsearch Rollup Jobs.
- `elastic_snapshot`: Manage Elasticsearch Snapshots.
- `elastic_snapshot_repository`: Manage Elasticsearch Snapshot Repositories.
- `elastic_transform`: Manage Elasticsearch Transform Jobs.
- `elastic_user`: Manage Elasticsearch users.

## Running the integration tests

* Requirements
  * [Python 3.5+](https://www.python.org/)
  * [pip](https://pypi.org/project/pip/)
  * [virtualenv](https://virtualenv.pypa.io/en/latest/) or [pipenv](https://pypi.org/project/pipenv/) if you prefer.
  * [git](https://git-scm.com/)
  * [docker](https://www.docker.com/)
  * [docker-compose](https://docs.docker.com/compose/)

* Useful Links
  * [Pip & Virtual Environments](https://docs.python-guide.org/dev/virtualenvs/)
  * [Ansible Integration Tests](https://docs.ansible.com/ansible/latest/dev_guide/testing_integration.html)

The ansible-test tool requires a specific directory hierarchy to function correctly so please follow carefully. Many of these test make use of docker-compose to launch Elastic Clusters. These tests should be run in a isolated Linux environment.

* Create the required directory structure. N-B. The ansible-test tool requires this format.

```bash
mkdir -p git/ansible_collections/community
cd git/ansible_collections/community
```

* Clone the required projects.

```bash
git clone  https://github.com/ansible-collections/community.elastic.git ./elastic
git clone  https://github.com/ansible-collections/community.general.git ./general
```

* Create and activate a virtual environment.

```bash
virtualenv venv
source venv/bin/activate
```

* Change to the project directory.

```bash
cd elastic
```

* Install the devel branch of ansible-base.

```bash
pip install https://github.com/ansible/ansible/archive/devel.tar.gz --disable-pip-version-check
```

Please note that most of these integration tests are intended to run directly in GitHUb Actions and running them locally may make changes to the executing computer. You can use the docker flag to avoid that but many of these tests won't work in those conditions.

* Run integration tests for the elastic_user module.

```bash
ansible-test integration -v --color yes --python 3.6 elastic_user
```

* Run integration tests for the elastic_cluster_health module.

```bash
ansible-test integration -v --color yes --python 3.6 elastic_cluster_health
```

* Run tests for everything in the collection.

```bash
ansible-test integration -v --color yes --python 3.6 
```
