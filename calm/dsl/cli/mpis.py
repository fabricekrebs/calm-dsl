import uuid
import click
from prettytable import PrettyTable

from calm.dsl.api import get_api_client, get_resource_api
from calm.dsl.config import get_config
from .utils import highlight_text, get_states_filter
from .bps import launch_blueprint_simple, get_blueprint
from .projects import get_project


def get_app_family_list():
    """returns the app family list categories"""

    client = get_api_client()
    Obj = get_resource_api("categories/AppFamily", client.connection)

    res, err = Obj.list(params={})
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    res = res.json()
    categories = []

    for entity in res["entities"]:
        categories.append(entity["value"])

    return categories


def get_group_data_value(data_list, field, value_list=False):
    """ to find the field value in group api call
        return whole list of values if value_list is True
    """

    for entity in data_list:
        if entity["name"] == field:
            entity_value = entity["values"]
            if not entity_value:
                return None

            return (
                entity_value[0]["values"]
                if value_list
                else entity_value[0]["values"][0]
            )

    return None


def trunc_string(data=None, max_length=50):

    if not data:
        return "-"

    if len(data) > max_length:
        return data[: max_length - 1] + "..."

    return data


def get_mpis_group_call(
    name=None,
    app_family="All",
    app_states=[],
    group_member_count=0,
    app_source=None,
    app_group_uuid=None,
):
    """
        To call groups() api for marketplace items
        if group_member_count is 0, it will not apply the group_count filter
    """

    client = get_api_client()
    filter = "marketplace_item_type_list==APP"

    if app_states:
        filter += get_states_filter(state_key="app_state", states=app_states)

    if app_family != "All":
        filter += ";category_name==AppFamily;category_value=={}".format(app_family)

    if name:
        filter += ";name=={}".format(name)

    if app_source:
        filter += ";app_source=={}".format(app_source)

    if app_group_uuid:
        filter += ";app_group_uuid=={}".format(app_group_uuid)

    payload = {
        "group_member_sort_attribute": "version",
        "group_member_sort_order": "DESCENDING",
        "grouping_attribute": "app_group_uuid",
        "group_count": 64,
        "group_offset": 0,
        "filter_criteria": filter,
        "entity_type": "marketplace_item",
        "group_member_attributes": [
            {"attribute": "name"},
            {"attribute": "author"},
            {"attribute": "version"},
            {"attribute": "categories"},
            {"attribute": "owner_reference"},
            {"attribute": "owner_username"},
            {"attribute": "project_names"},
            {"attribute": "project_uuids"},
            {"attribute": "app_state"},
            {"attribute": "description"},
            {"attribute": "spec_version"},
            {"attribute": "app_attribute_list"},
            {"attribute": "app_group_uuid"},
            {"attribute": "icon_list"},
            {"attribute": "change_log"},
            {"attribute": "app_source"},
        ],
    }

    if group_member_count:
        payload["group_member_count"] = group_member_count

    Obj = get_resource_api("groups", client.connection)
    res, err = Obj.create(payload=payload)

    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    res = res.json()
    return res


def get_marketplace_items(name, quiet, app_family, display_all):
    """Lists marketplace items"""

    group_member_count = 0
    if not display_all:
        group_member_count = 1

    res = get_mpis_group_call(
        name=name,
        app_family=app_family,
        app_states=["PUBLISHED"],
        group_member_count=group_member_count,
    )
    group_results = res["group_results"]

    if quiet:
        for group in group_results:
            entity_results = group["entity_results"]
            entity_data = entity_results[0]["data"]
            click.echo(highlight_text(get_group_data_value(entity_data, "name")))
        return

    table = PrettyTable()
    field_names = ["NAME", "DESCRIPTION", "AUTHOR", "APP_SOURCE"]
    if display_all:
        field_names.insert(1, "VERSION")
        field_names.insert(2, "AVAILABLE TO")
        field_names.append("UUID")

    table.field_names = field_names

    for group in group_results:
        entity_results = group["entity_results"]

        for entity in entity_results:
            entity_data = entity["data"]
            project_names = get_group_data_value(
                entity_data, "project_names", value_list=True
            )
            available_to = "-"
            if project_names:
                project_count = len(project_names)
                if project_count == 1:
                    available_to = "{} Project".format(project_count)
                else:
                    available_to = "{} Projects".format(project_count)

            description = get_group_data_value(entity_data, "description")

            data_row = [
                highlight_text(get_group_data_value(entity_data, "name")),
                highlight_text(
                    trunc_string(get_group_data_value(entity_data, "description"))
                ),
                highlight_text(get_group_data_value(entity_data, "author")),
                highlight_text(get_group_data_value(entity_data, "app_source")),
            ]

            if display_all:
                data_row.insert(
                    1, highlight_text(get_group_data_value(entity_data, "version"))
                )
                data_row.insert(2, highlight_text(available_to))
                data_row.append(highlight_text(entity["entity_id"]))

            table.add_row(data_row)

    click.echo(table)


def get_marketplace_bps(name, quiet, app_family, app_states=[]):
    """ List all the blueprints in marketplace manager"""

    res = get_mpis_group_call(name=name, app_family=app_family, app_states=app_states)
    group_results = res["group_results"]

    if quiet:
        for group in group_results:
            entity_results = group["entity_results"]
            entity_data = entity_results[0]["data"]
            click.echo(highlight_text(get_group_data_value(entity_data, "name")))
        return

    table = PrettyTable()
    field_names = [
        "NAME",
        "APP_SOURCE",
        "OWNER",
        "AUTHOR",
        "AVAILABLE TO",
        "VERSION",
        "CATEGORY",
        "STATUS",
        "UUID",
    ]

    table.field_names = field_names

    for group in group_results:
        entity_results = group["entity_results"]

        for entity in entity_results:
            entity_data = entity["data"]
            project_names = get_group_data_value(
                entity_data, "project_names", value_list=True
            )
            available_to = "-"
            if project_names:
                project_count = len(project_names)
                if project_count == 1:
                    available_to = "{} Project".format(project_count)
                else:
                    available_to = "{} Projects".format(project_count)

            categories = get_group_data_value(entity_data, "categories")
            category = "-"
            if categories:
                category = categories.split(":")[1]

            owner = get_group_data_value(entity_data, "owner_username")
            if not owner:
                owner = "-"

            data_row = [
                highlight_text(get_group_data_value(entity_data, "name")),
                highlight_text(get_group_data_value(entity_data, "app_source")),
                highlight_text(owner),
                highlight_text(get_group_data_value(entity_data, "author")),
                highlight_text(available_to),
                highlight_text(get_group_data_value(entity_data, "version")),
                highlight_text(category),
                highlight_text(get_group_data_value(entity_data, "app_state")),
                highlight_text(entity["entity_id"]),
            ]

            table.add_row(data_row)

    click.echo(table)


def get_mpi_latest_version(name, app_source=None, app_states=[]):

    res = get_mpis_group_call(
        name=name, app_states=app_states, group_member_count=1, app_source=app_source
    )
    group_results = res["group_results"]

    if not group_results:
        raise Exception("No MPI found with name {}".format(name))

    entity_results = group_results[0]["entity_results"]
    entity_version = get_group_data_value(entity_results[0]["data"], "version")

    return entity_version


def get_mpi_by_name_n_version(name, version, app_states=[], app_source=None):
    """
    It will fetch marketplace item with particular version.
    Special case: As blueprint with state REJECTED and other can coexist with same name and version
    """

    client = get_api_client()
    filter = "name==" + name + ";version==" + version

    if app_states:
        filter += get_states_filter(state_key="app_state", states=app_states)

    if app_source:
        filter += ";app_source=={}".format(app_source)

    payload = {
        "length": 250,
        "filter": filter,
    }
    res, err = client.market_place.list(params=payload)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    res = res.json()
    if not res["entities"]:
        message = "no mpi found with name {} and version {}.\nRun 'calm get mpis -d' to get detailed list of mpis".format(
            name, version
        )
        raise Exception(message)

    app_uuid = res["entities"][0]["metadata"]["uuid"]
    res, err = client.market_place.read(app_uuid)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    res = res.json()
    return res


def describe_marketplace_item(name, version=None, app_source=None):
    """describes the marketplace blueprint related to marketplace item"""

    describe_marketplace_bp(
        name=name, version=version, app_source=app_source, app_state="PUBLISHED"
    )


def describe_marketplace_bp(name, version=None, app_source=None, app_state=None):
    """describes the marketplace blueprint"""

    app_states = [app_state] if app_state else []
    if not version:
        click.echo(
            "Fetching latest version of Marketplace Blueprint {} ...".format(name),
            nl=False,
        )
        version = get_mpi_latest_version(
            name=name, app_source=app_source, app_states=app_states
        )
        click.echo("[{}]".format(version))

    bp = get_mpi_by_name_n_version(
        name=name, version=version, app_states=app_states, app_source=app_source
    )

    click.echo("\n----MarketPlace Blueprint Summary----\n")
    click.echo(
        "Name: "
        + highlight_text(name)
        + " (uuid: "
        + highlight_text(bp["metadata"]["uuid"])
        + ")"
    )
    click.echo("Description: " + highlight_text(bp["status"]["description"]))
    click.echo("App State: " + highlight_text(bp["status"]["resources"]["app_state"]))
    click.echo("Author: " + highlight_text(bp["status"]["resources"]["author"]))

    project_name_list = bp["status"]["resources"]["project_reference_list"]
    click.echo(
        "Projects shared with [{}]: ".format(highlight_text(len(project_name_list)))
    )
    for project in project_name_list:
        click.echo("\t{}".format(highlight_text(project["name"])))

    categories = bp["metadata"].get("categories", {})
    if categories:
        click.echo("Categories [{}]: ".format(highlight_text(len(categories))))
        for key, value in categories.items():
            click.echo("\t {} : {}".format(highlight_text(key), highlight_text(value)))

    change_log = bp["status"]["resources"]["change_log"]
    if not change_log:
        change_log = "No logs present"

    click.echo("Change Log: " + highlight_text(change_log))
    click.echo("Version: " + highlight_text(bp["status"]["resources"]["version"]))
    click.echo("App Source: " + highlight_text(bp["status"]["resources"]["app_source"]))

    blueprint_template = bp["status"]["resources"]["app_blueprint_template"]
    action_list = blueprint_template["status"]["resources"]["app_profile_list"][0][
        "action_list"
    ]
    click.echo("App actions [{}]: ".format(highlight_text(len(action_list))))
    for action in action_list:
        click.echo("\t{} : ".format(highlight_text(action["name"])), nl=False)
        click.echo(
            highlight_text(
                action["description"]
                if action["description"]
                else "No description avaiable"
            )
        )


def launch_marketplace_bp(
    name,
    version,
    project,
    app_name=None,
    profile_name=None,
    patch_editables=True,
    app_source=None,
):
    """
        Launch marketplace blueprints
        If version not there search in published, pendingm, accepted blueprints
    """

    client = get_api_client()
    config = get_config()

    if not version:
        version = get_mpi_latest_version(name=name, app_source=app_source)

    bp_payload = create_marketplace_blueprint(
        name=name, version=version, project_name=project, app_source=app_source
    )

    bp_name = bp_payload["metadata"].get("name")

    app_name = app_name or "Mpi-App-{}-{}".format(name, str(uuid.uuid4())[-10:])
    click.echo("Launching mpi blueprint {} to create app {}".format(bp_name, app_name))
    launch_blueprint_simple(
        client,
        patch_editables=patch_editables,
        profile_name=profile_name,
        app_name=app_name,
        blueprint=bp_payload,
    )


def launch_marketplace_item(
    name,
    version,
    project,
    app_name=None,
    profile_name=None,
    patch_editables=True,
    app_source=None,
):
    """
        Launch marketplace items
        If version not there search in published blueprints
    """

    client = get_api_client()
    config = get_config()

    if not version:
        version = get_mpi_latest_version(
            name=name, app_source=app_source, app_states=["PUBLISHED"]
        )

    bp_payload = create_marketplace_blueprint(
        name=name, version=version, project_name=project, app_source=app_source
    )

    bp_name = bp_payload["metadata"].get("name")

    click.echo("Launching mpi blueprint {} ...".format(bp_name))
    app_name = app_name or "Mpi-App-{}-{}".format(name, str(uuid.uuid4())[-10:])
    launch_blueprint_simple(
        client,
        patch_editables=patch_editables,
        profile_name=profile_name,
        app_name=app_name,
        blueprint=bp_payload,
    )


def create_marketplace_blueprint(name, version, project_name=None, app_source=None):

    client = get_api_client()
    config = get_config()

    project_name = project_name or config["PROJECT"]["name"]
    project_data = get_project(client, project_name)

    project_uuid = project_data["metadata"]["uuid"]

    click.echo("Fetching environment data ...", nl=False)
    res, err = client.project.read(project_uuid)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))
    click.echo("[Success]")

    res = res.json()
    environments = res["status"]["project_status"]["resources"][
        "environment_reference_list"
    ]

    # For now only single environment exists
    env_uuid = environments[0]["uuid"]

    click.echo("Fetching mpi store item ...", nl=False)
    mpi_data = get_mpi_by_name_n_version(
        name=name,
        version=version,
        app_source=app_source,
        app_states=["PENDING", "ACCEPTED", "PUBLISHED"],
    )
    click.echo("[Success]")

    bp_spec = {}
    bp_spec["spec"] = mpi_data["spec"]["resources"]["app_blueprint_template"]["spec"]
    del bp_spec["spec"]["name"]
    bp_spec["spec"]["environment_uuid"] = env_uuid

    bp_spec["spec"]["app_blueprint_name"] = "Mpi-Bp-{}-{}".format(
        name, str(uuid.uuid4())[-10:]
    )

    bp_spec["metadata"] = {
        "kind": "blueprint",
        "project_reference": {"kind": "project", "uuid": project_uuid},
        "categories": mpi_data["metadata"].get("categories", {}),
    }
    bp_spec["api_version"] = "3.0"

    click.echo("Creating mpi blueprint ...", nl=False)
    bp_res, err = client.blueprint.marketplace_launch(bp_spec)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))
    click.echo("[Success]")

    bp_res = bp_res.json()

    del bp_res["spec"]["environment_uuid"]
    bp_status = bp_res["status"]["state"]
    if bp_status != "ACTIVE":
        raise Exception("blueprint went to {} state".format(bp_status))

    return bp_res


def publish_bp_to_marketplace_manager(
    bp_name,
    marketplace_bp_name,
    version,
    description="",
    with_secrets=False,
    app_group_uuid=None,
):

    client = get_api_client()
    config = get_config()
    bp = get_blueprint(client, bp_name)
    bp_uuid = bp.get("metadata", {}).get("uuid", "")

    if with_secrets:
        bp_data, err = client.blueprint.export_json_with_secrets(bp_uuid)

    else:
        bp_data, err = client.blueprint.export_json(bp_uuid)

    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    bp_data = bp_data.json()
    bp_template = {
        "spec": {
            "name": marketplace_bp_name,
            "description": description,
            "resources": {
                "app_attribute_list": ["FEATURED"],
                "icon_reference_list": [],
                "author": config["SERVER"]["pc_username"],
                "version": version,
                "app_group_uuid": app_group_uuid or str(uuid.uuid4()),
                "app_blueprint_template": {
                    "status": bp_data["status"],
                    "spec": bp_data["spec"],
                },
            },
        },
        "api_version": "3.0",
        "metadata": {"kind": "marketplace_item"},
    }

    res, err = client.market_place.create(bp_template)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))


def publish_bp_as_new_marketplace_bp(
    bp_name, marketplace_bp_name, version, description="", with_secrets=False,
):

    # Search whether this marketplace item exists or not
    res = get_mpis_group_call(
        name=marketplace_bp_name, group_member_count=1, app_source="LOCAL"
    )
    group_count = res["filtered_group_count"]

    if group_count:
        raise Exception(
            "A local marketplace item exists with same name ({}) in another app family".format(
                marketplace_bp_name
            )
        )

    publish_bp_to_marketplace_manager(
        bp_name=bp_name,
        marketplace_bp_name=marketplace_bp_name,
        version=version,
        description=description,
        with_secrets=with_secrets,
    )


def publish_bp_as_existing_marketplace_bp(
    bp_name, marketplace_bp_name, version, description="", with_secrets=False
):

    res = get_mpis_group_call(
        name=marketplace_bp_name, group_member_count=1, app_source="LOCAL"
    )
    group_results = res["group_results"]
    if not group_results:
        raise Exception(
            "No local marketplace blueprint exists with name {}".format(
                marketplace_bp_name
            )
        )

    entity_group = group_results[0]
    app_group_uuid = entity_group["group_by_column_value"]

    # Search whether given version of marketplace items already exists or not
    # Rejected MPIs with same name and version can exist
    res = get_mpis_group_call(
        app_group_uuid=app_group_uuid, app_states=["PUBLISHED", "PENDING", "ACCEPTED"]
    )

    group_results = res["group_results"]
    entity_results = group_results[0]["entity_results"]

    for entity in entity_results:
        entity_version = get_group_data_value(entity["data"], "version")
        entity_app_state = get_group_data_value(entity["data"], "app_state")

        if entity_version == version:
            raise Exception(
                "An item exists with same version ({}) and app_state ({}) in the chosen app family.".format(
                    entity_version, entity_app_state
                )
            )

    publish_bp_to_marketplace_manager(
        bp_name=bp_name,
        marketplace_bp_name=marketplace_bp_name,
        version=version,
        description=description,
        with_secrets=with_secrets,
        app_group_uuid=app_group_uuid,
    )


def approve_marketplace_bp(bp_name, version=None, projects=[], category=None):

    client = get_api_client()
    if not version:
        # Search for pending blueprints, Only those blueprints can be approved
        version = get_mpi_latest_version(name=bp_name, app_states=["PENDING"])

    bp = get_mpi_by_name_n_version(
        name=bp_name, version=version, app_source="LOCAL", app_states=["PENDING"]
    )
    bp_uuid = bp["metadata"]["uuid"]

    res, err = client.market_place.read(bp_uuid)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    bp_data = res.json()
    bp_data.pop("status", None)
    bp_data["api_version"] = "3.0"
    bp_data["spec"]["resources"]["app_state"] = "ACCEPTED"

    if category:
        app_families = get_app_family_list()
        if category not in app_families:
            raise Exception("{} is not a valid App Family category".format(category))

        bp_data["metadata"]["categories"] = {"AppFamily": category}

    for project in projects:
        project_data = get_project(client, project)

        bp_data["spec"]["resources"]["project_reference_list"].append(
            {
                "kind": "project",
                "name": project,
                "uuid": project_data["metadata"]["uuid"],
            }
        )

    res, err = client.market_place.update(uuid=bp_uuid, payload=bp_data)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))


def publish_marketplace_bp(
    bp_name, version=None, projects=[], category=None, app_source=None
):

    client = get_api_client()
    if not version:
        # Search for accepted blueprints, only those blueprints can be published
        version = get_mpi_latest_version(
            name=bp_name, app_states=["ACCEPTED"], app_source=app_source
        )

    bp = get_mpi_by_name_n_version(
        name=bp_name, version=version, app_source=app_source, app_states=["ACCEPTED"]
    )
    bp_uuid = bp["metadata"]["uuid"]

    res, err = client.market_place.read(bp_uuid)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    bp_data = res.json()
    bp_data.pop("status", None)
    bp_data["api_version"] = "3.0"
    bp_data["spec"]["resources"]["app_state"] = "PUBLISHED"

    if category:
        app_families = get_app_family_list()
        if category not in app_families:
            raise Exception("{} is not a valid App Family category".format(category))

        bp_data["metadata"]["categories"] = {"AppFamily": category}

    if projects:
        # Clear the stored projects
        bp_data["spec"]["resources"]["project_reference_list"] = []
        for project in projects:
            project_data = get_project(client, project)

            bp_data["spec"]["resources"]["project_reference_list"].append(
                {
                    "kind": "project",
                    "name": project,
                    "uuid": project_data["metadata"]["uuid"],
                }
            )

    # Atleast 1 project required for publishing to marketplace
    if not bp_data["spec"]["resources"]["project_reference_list"]:
        raise Exception(
            "To publish to the Marketplace, please provide a project first."
        )

    res, err = client.market_place.update(uuid=bp_uuid, payload=bp_data)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))


def update_marketplace_bp(
    name, version, category=None, projects=[], description=None, app_source=None
):
    """
        updates the marketplace bp
        version is required to prevent unwanted update of another mpi    
    """

    client = get_api_client()
    mpi_data = get_mpi_by_name_n_version(
        name=name,
        version=version,
        app_source=app_source,
        app_states=["PENDING", "ACCEPTED", "PUBLISHED"],
    )
    bp_uuid = mpi_data["metadata"]["uuid"]

    res, err = client.market_place.read(bp_uuid)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    bp_data = res.json()
    bp_data.pop("status", None)
    bp_data["api_version"] = "3.0"

    if category:
        app_families = get_app_family_list()
        if category not in app_families:
            raise Exception("{} is not a valid App Family category".format(category))

        bp_data["metadata"]["categories"] = {"AppFamily": category}

    if projects:
        # Clear all stored projects
        bp_data["spec"]["resources"]["project_reference_list"] = []
        for project in projects:
            project_data = get_project(client, project)

            bp_data["spec"]["resources"]["project_reference_list"].append(
                {
                    "kind": "project",
                    "name": project,
                    "uuid": project_data["metadata"]["uuid"],
                }
            )

    if description:
        bp_data["spec"]["description"] = description

    res, err = client.market_place.update(uuid=bp_uuid, payload=bp_data)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))


def delete_marketplace_bp(name, version, app_source=None, app_state=None):

    client = get_api_client()

    if app_state == "PUBLISHED":
        raise Exception("Unpublish mpi {} first to delete".format(name))

    app_states = [app_state] if app_state else ["ACCEPTED", "REJECTED", "PENDING"]
    mpi_data = get_mpi_by_name_n_version(
        name=name, version=version, app_source=app_source, app_states=app_states
    )
    bp_uuid = mpi_data["metadata"]["uuid"]

    res, err = client.market_place.delete(bp_uuid)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))


def reject_marketplace_bp(name, version):

    client = get_api_client()
    if not version:
        # Search for pending blueprints, Only those blueprints can be rejected
        version = get_mpi_latest_version(name=name, app_states=["PENDING"])

    # Pending BP will always of type LOCAL, so no need to apply that filter
    bp = get_mpi_by_name_n_version(name=name, version=version, app_states=["PENDING"])
    bp_uuid = bp["metadata"]["uuid"]

    res, err = client.market_place.read(bp_uuid)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    bp_data = res.json()
    bp_data.pop("status", None)
    bp_data["api_version"] = "3.0"
    bp_data["spec"]["resources"]["app_state"] = "REJECTED"

    res, err = client.market_place.update(uuid=bp_uuid, payload=bp_data)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))


def unpublish_marketplace_bp(name, version, app_source=None):

    client = get_api_client()
    if not version:
        # Search for published blueprints, only those can be unpublished
        version = get_mpi_latest_version(
            name=name, app_states=["PUBLISHED"], app_source=app_source
        )

    bp = get_mpi_by_name_n_version(
        name=name, version=version, app_states=["PUBLISHED"], app_source=app_source
    )
    bp_uuid = bp["metadata"]["uuid"]

    res, err = client.market_place.read(bp_uuid)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    bp_data = res.json()
    bp_data.pop("status", None)
    bp_data["api_version"] = "3.0"
    bp_data["spec"]["resources"]["app_state"] = "ACCEPTED"

    res, err = client.market_place.update(uuid=bp_uuid, payload=bp_data)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))
