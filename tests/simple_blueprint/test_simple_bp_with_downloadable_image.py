import json

from calm.dsl.builtins import SimpleDeployment, SimpleBlueprint
from calm.dsl.builtins import read_provider_spec, Ref, Metadata
from calm.dsl.builtins import read_local_file, basic_cred
from calm.dsl.builtins import vm_disk_package

DSL_CONFIG = json.loads(read_local_file(".tests/config.json"))

CRED_USERNAME = read_local_file(".tests/username")
CRED_PASSWORD = read_local_file(".tests/password")

# OS Image details for VM
CENTOS_IMAGE_SOURCE = "http://download.nutanix.com/calm/CentOS-7-x86_64-1810.qcow2"
CentosPackage = vm_disk_package(
    name="centos_disk",
    config={"image": {"source": CENTOS_IMAGE_SOURCE}},
)

# project constants
PROJECT = DSL_CONFIG["PROJECTS"]["PROJECT1"]
PROJECT_NAME = PROJECT["NAME"]
NTNX_LOCAL_ACCOUNT = DSL_CONFIG["ACCOUNTS"]["NTNX_LOCAL_AZ"]
SUBNET_UUID = NTNX_LOCAL_ACCOUNT["SUBNETS"][0]["UUID"]

Centos = basic_cred(CRED_USERNAME, CRED_PASSWORD, name="default cred", default=True)


class VmDeployment(SimpleDeployment):
    """Single VM service"""

    # VM Spec
    provider_spec = read_provider_spec("specs/ahv_provider_spec.yaml")
    provider_spec.spec["resources"]["nic_list"][0]["subnet_reference"][
        "uuid"
    ] = SUBNET_UUID


class SimpleLampBlueprint(SimpleBlueprint):
    """Simple blueprint Spec"""

    credentials = [Centos]
    deployments = [VmDeployment]
    packages = [CentosPackage]  # add downloadable image packages here


class BpMetadata(Metadata):

    project = Ref.Project(PROJECT_NAME)
