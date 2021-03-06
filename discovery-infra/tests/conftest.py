import logging
import os
import test_infra.utils as infra_utils
from distutils import util
from pathlib import Path

import pytest
from test_infra import assisted_service_api, consts, utils

qe_env = False


def is_qe_env():
    return os.environ.get('NODE_ENV') == 'QE_VM'


# TODO changes it
if is_qe_env():
    from test_infra.controllers.node_controllers.qe_vm_controler import \
        QeVmController as nodeController
    qe_env = True
else:
    from test_infra.controllers.node_controllers.terraform_controller import \
        TerraformController as nodeController


private_ssh_key_path_default = os.path.join(os.getcwd(), "ssh_key/key") if not qe_env else \
    os.path.join(str(Path.home()), ".ssh/id_rsa")

env_variables = {"ssh_public_key": utils.get_env('SSH_PUB_KEY'),
                 "remote_service_url": utils.get_env('REMOTE_SERVICE_URL'),
                 "pull_secret": utils.get_env('PULL_SECRET'),
                 "offline_token": utils.get_env('OFFLINE_TOKEN'),
                 "openshift_version": utils.get_env('OPENSHIFT_VERSION', '4.6'),
                 "base_domain": utils.get_env('BASE_DOMAIN', "redhat.com"),
                 "num_masters": int(utils.get_env('NUM_MASTERS', consts.NUMBER_OF_MASTERS)),
                 "num_workers": max(2, int(utils.get_env('NUM_WORKERS', 0))),
                 "vip_dhcp_allocation": bool(util.strtobool(utils.get_env('VIP_DHCP_ALLOCATION'))),
                 "machine_cidr": utils.get_env('NETWORK_CIDR', '192.168.126.0/24'),
                 "worker_memory": int(utils.get_env('WORKER_MEMORY', '8892')),
                 "master_memory": int(utils.get_env('MASTER_MEMORY', '16984')),
                 "network_mtu": utils.get_env('NETWORK_MTU', '1500'),
                 "worker_disk": int(utils.get_env('WORKER_DISK', '21474836480')),
                 "master_disk": int(utils.get_env('MASTER_DISK', '128849018880')),
                 "storage_pool_path": utils.get_env('STORAGE_POOL_PATH', os.path.join(os.getcwd(), "storage_pool")),
                 "cluster_name": utils.get_env('CLUSTER_NAME', f'{consts.CLUSTER_PREFIX}'),
                 "private_ssh_key_path": utils.get_env('PRIVATE_KEY_PATH', private_ssh_key_path_default),
                 "kubeconfig_path": utils.get_env('KUBECONFIG', ''),
                 "log_folder": utils.get_env('LOG_FOLDER', consts.LOG_FOLDER)}

cluster_mid_name = infra_utils.get_random_name()

# Tests running on terraform parallel must have unique ISO file
if not qe_env:
    image = utils.get_env('ISO',
                          os.path.join(consts.IMAGE_FOLDER, f'{env_variables["cluster_name"]}-{cluster_mid_name}-'
                                                            f'installer-image.iso')).strip()
    env_variables["kubeconfig_path"] = f'/tmp/test_kubeconfig_{cluster_mid_name}'
else:
    image = utils.get_env('ISO',
                          os.path.join(consts.IMAGE_FOLDER, f'{env_variables["cluster_name"]}-installer-image.iso')).\
        strip()

env_variables["iso_download_path"] = image
env_variables["num_nodes"] = env_variables["num_workers"] + env_variables["num_masters"]


@pytest.fixture(scope="session")
def api_client():
    logging.info(f'--- SETUP --- api_client\n')
    yield get_api_client()


def get_api_client(offline_token=env_variables['offline_token'], **kwargs):
    url = env_variables['remote_service_url']

    if not url:
        url = utils.get_local_assisted_service_url(
            utils.get_env('PROFILE'), utils.get_env('NAMESPACE'), 'assisted-service', utils.get_env('DEPLOY_TARGET'))
    
    return assisted_service_api.create_client(url, offline_token, **kwargs)


@pytest.fixture(scope="session")
def setup_node_controller():
    logging.info(f'--- SETUP --- node controller\n')
    yield nodeController
    logging.info(f'--- TEARDOWN --- node controller\n')


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()

    setattr(item, "result_" + result.when, result)
