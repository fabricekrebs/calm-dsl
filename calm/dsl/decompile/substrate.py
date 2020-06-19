from ruamel import yaml
import os

from calm.dsl.decompile.render import render_template
from calm.dsl.decompile.credential import get_cred_var_name
from calm.dsl.decompile.action import render_action_template
from calm.dsl.decompile.readiness_probe import render_readiness_probe_template
from calm.dsl.decompile.file_handler import get_specs_dir, get_specs_dir_key
from calm.dsl.builtins import SubstrateType, get_valid_identifier
from calm.dsl.decompile.ref_dependency import update_substrate_name
from calm.dsl.tools import get_logging_handle

LOG = get_logging_handle(__name__)


def render_substrate_template(cls, vm_images=[]):

    LOG.debug("Rendering {} substrate template".format(cls.__name__))
    if not isinstance(cls, SubstrateType):
        raise TypeError("{} is not of type {}".format(cls, SubstrateType))

    # Entity context
    entity_context = "Substrate_" + cls.__name__

    user_attrs = cls.get_user_attrs()
    user_attrs["name"] = cls.__name__
    user_attrs["description"] = cls.__doc__ or "{} Substrate description".format(
        cls.__name__
    )

    # Update substrate name map and gui name
    gui_display_name = getattr(cls, "display_name", "")
    if not gui_display_name:
        gui_display_name = cls.__name__

    elif gui_display_name != cls.__name__:
        user_attrs["gui_display_name"] = gui_display_name

    # updating ui and dsl name mapping
    update_substrate_name(gui_display_name, cls.__name__)

    provider_spec_editables = user_attrs.get("provider_spec_editables", {})
    create_spec_editables = provider_spec_editables.get("create_spec", {})
    readiness_probe_editables = provider_spec_editables.get("readiness_probe", {})

    # Handle readiness probe for substrate
    rp_editable_list = []
    for k, v in readiness_probe_editables.items():
        if v:
            rp_editable_list.append(k)

    # Appending readiness_probe editables to readiness_probe object
    readiness_probe = user_attrs["readiness_probe"]
    readiness_probe.editables_list = rp_editable_list
    user_attrs["readiness_probe"] = render_readiness_probe_template(
        user_attrs["readiness_probe"]
    )

    spec_dir = get_specs_dir()

    # Handle create spec runtime editables
    if create_spec_editables:
        create_spec_editable_file_name = cls.__name__ + "_create_spec_editables.yaml"
        file_location = os.path.join(spec_dir, create_spec_editable_file_name)
        user_attrs["provider_spec_editables"] = "read_spec('{}')".format(
            os.path.join(get_specs_dir_key(), create_spec_editable_file_name)
        )

        # Write editable spec to separate file
        with open(file_location, "w+") as fd:
            fd.write(yaml.dump(create_spec_editables, default_flow_style=False))

    # Handle provider_spec for substrate
    provider_spec = cls.provider_spec
    # creating a file for storing provider_spec
    provider_spec_file_name = cls.__name__ + "_provider_spec.yaml"
    user_attrs["provider_spec"] = get_provider_spec_string(
        spec=provider_spec,
        filename=os.path.join(get_specs_dir_key(), provider_spec_file_name),
        provider_type=cls.provider_type,
        vm_images=vm_images,
    )

    # Write provider spec to separate file
    file_location = os.path.join(spec_dir, provider_spec_file_name)
    with open(file_location, "w+") as fd:
        fd.write(yaml.dump(provider_spec, default_flow_style=False))

    # Actions
    action_list = []
    system_actions = {v: k for k, v in SubstrateType.ALLOWED_FRAGMENT_ACTIONS.items()}
    for action in user_attrs.get("actions", []):
        if action.__name__ in list(system_actions.keys()):
            action.name = system_actions[action.__name__]
            action.__name__ = system_actions[action.__name__]
        action_list.append(render_action_template(action, entity_context))

    user_attrs["actions"] = action_list

    text = render_template(schema_file="substrate.py.jinja2", obj=user_attrs)
    return text.strip()


def get_provider_spec_string(spec, filename, provider_type, vm_images):

    if provider_type == "AHV_VM":
        import pdb; pdb.set_trace()
        from calm.dsl.builtins import AhvVmType, AhvVmResourcesType
        AhvVmType.decompile(spec)
        disk_list = spec["resources"]["disk_list"]

        disk_ind_img_map = {}
        for ind, disk in enumerate(disk_list):
            data_source_ref = disk.get("data_source_reference", {})
            if data_source_ref:
                if data_source_ref.get("kind") == "app_package":
                    disk_ind_img_map[ind + 1] = get_valid_identifier(
                        data_source_ref.get("name")
                    )
                    data_source_ref.pop("uuid", None)

        disk_pkg_string = ""
        for k, v in disk_ind_img_map.items():
            disk_pkg_string += ",{}: {}".format(k, v)
        if disk_pkg_string.startswith(","):
            disk_pkg_string = disk_pkg_string[1:]
        disk_pkg_string = "{" + disk_pkg_string + "}"

        res = "read_ahv_spec('{}', disk_packages = {})".format(
            filename, disk_pkg_string
        )

    elif provider_type == "VMWARE_VM":
        spec_template = get_valid_identifier(spec["template"])

        if spec_template in vm_images:
            spec["template"] = ""
            res = "read_vmw_spec('{}', vm_template={})".format(filename, spec_template)

        else:
            res = "read_vmw_spec('{}')".format(filename)

    else:
        res = "read_provider_spec('{}')".format(filename)

    return res
