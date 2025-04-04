from datetime import datetime
from .__about__ import __version__
from glob import glob
import os
# When Tutor drops support for Python 3.8, we'll need to update this to:
# from importlib import resources as importlib_resources
# See: https://github.com/overhangio/tutor/issues/966#issuecomment-1938681102
import importlib_resources
import click
from tutor import hooks
from tutor import config as tutor_config
from tutor.commands.local import local as local_command_group
from tutor.commands.k8s import k8s as k8s_command_group, K8sTaskRunner


config = {
    "defaults": {
        "VERSION": __version__,
        "BASE_IMAGE": "docker.io/ubuntu:22.04",
        "DOCKER_IMAGE": "{{ DOCKER_REGISTRY }}backup:{{ BACKUP_VERSION }}",  # noqa: E501
        "K8S_CRONJOB_HISTORYLIMIT_FAILURE": 1,
        "K8S_CRONJOB_HISTORYLIMIT_SUCCESS": 3,
        "K8S_CRONJOB_STARTING_DEADLINE_SECONDS": 900,
        "K8S_CRONJOB_BACKUP_ENABLE": True,
        "K8S_CRONJOB_BACKUP_SCHEDULE": "0 0 * * *",
        "K8S_CRONJOB_RESTORE_ENABLE": False,
        "K8S_CRONJOB_RESTORE_SCHEDULE": "30 0 * * *",
        "K8S_CRONJOB_CONCURRENCYPOLICY": "Forbid",
        "K8S_USE_EPHEMERAL_VOLUMES": False,
        "K8S_EPHEMERAL_VOLUME_SIZE": "10Gi",
        "S3_HOST": "{{ S3_HOST | default('') }}",
        "S3_PORT": "{{ S3_PORT | default('') }}",
        "S3_REGION_NAME": "{{ S3_REGION | default('') }}",
        "S3_SIGNATURE_VERSION": "{{ S3_SIGNATURE_VERSION | default('s3v4') }}",
        "S3_ADDRESSING_STYLE": "{{ S3_ADDRESSING_STYLE | default('auto') }}",
        "S3_USE_SSL": "{{ S3_USE_SSL | default('True') }}",
        "S3_ACCESS_KEY": "{{ OPENEDX_AWS_ACCESS_KEY }}",
        "S3_SECRET_ACCESS_KEY": "{{ OPENEDX_AWS_SECRET_ACCESS_KEY }}",
        "S3_BUCKET_NAME": "backups",
        "MYSQL_DATABASES": [],
        "MONGODB_DATABASES": [],
        "MONGODB_AUTHENTICATION_DATABASE": "admin",
        "MONGORESTORE_ADDITIONAL_OPTIONS": "",
        "MYSQL_SINGLE_TRANSACTION": True,
        "MYSQL_FLUSH_LOGS": True,
    }
}

hooks.Filters.IMAGES_BUILD.add_item((
    "backup",
    ("plugins", "backup", "build", "backup"),
    "{{ BACKUP_DOCKER_IMAGE }}",
    (),
))
hooks.Filters.IMAGES_PULL.add_item((
    "backup",
    "{{ BACKUP_DOCKER_IMAGE }}",
))
hooks.Filters.IMAGES_PUSH.add_item((
    "backup",
    "{{ BACKUP_DOCKER_IMAGE }}",
))


@local_command_group.command(help="Backup MySQL, MongoDB, and Caddy")
@click.pass_obj
def backup(context):
    config = tutor_config.load(context.root)

    command = "python backup_services.py"
    web_proxy_enabled = config["ENABLE_WEB_PROXY"]
    https_enabled = config["ENABLE_HTTPS"]
    caddy_data_directory_exists = web_proxy_enabled and https_enabled
    if not caddy_data_directory_exists:
        command += " --exclude=caddy"

    job_runner = context.job_runner(config)
    job_runner.run_task(service="backup", command=command)


@local_command_group.command(help="Restore MySQL, MongoDB, and Caddy")
@click.pass_obj
@click.option(
    '--exclude',
    type=click.Choice(['mysql', 'mongodb', 'caddy']),
    multiple=True,
    help="Exclude services from restore"
)
@click.option('--date', type=click.DateTime(formats=["%Y-%m-%d"]),
              default=str(datetime.today().date()),
              help="Backup date (YYYY-MM-DD)")
def restore(context, exclude, date):
    config = tutor_config.load(context.root)
    command = f"python restore_services.py --date={date.date()}"
    if 'caddy' not in exclude:
        web_proxy_enabled = config["ENABLE_WEB_PROXY"]
        https_enabled = config["ENABLE_HTTPS"]
        caddy_data_directory_exists = web_proxy_enabled and https_enabled
        if not caddy_data_directory_exists:
            exclude = (*exclude, "caddy")

    for service in exclude:
        command += f" --exclude={service}"

    job_runner = context.job_runner(config)
    job_runner.run_task(service="backup", command=command)


@k8s_command_group.command(help="Backup MySQL, MongoDB, and Caddy")
@click.pass_obj
def backup(context):  # noqa: F811
    config = tutor_config.load(context.root)

    command = "python backup_services.py --upload"
    caddy_data_directory_exists = config["ENABLE_WEB_PROXY"]
    if not caddy_data_directory_exists:
        command += " --exclude=caddy"

    job_runner = K8sTaskRunner(context.root, config)
    job_runner.run_task(service="backup-restore", command=command)


@k8s_command_group.command(help="restore MySQL, MongoDB, and Caddy")
@click.pass_obj
@click.option('--date', type=click.DateTime(formats=["%Y-%m-%d"]),
              default=str(datetime.today().date()),
              help="Backup date (YYYY-MM-DD)")
@click.option('--version', default="", type=str,
              help="Version ID of the backup file")
@click.option(
    '--exclude',
    type=click.Choice(['mysql', 'mongodb', 'caddy']),
    multiple=True,
    help="Exclude services from restore"
)
@click.option('--list-versions', is_flag=False, flag_value=20, type=int,
              help="List n latest backup versions (n=20 by default)")
def restore(context, date, version, exclude, list_versions):  # noqa: F811
    config = tutor_config.load(context.root)

    command = f"python restore_services.py --date={date.date()}"
    if list_versions:
        command += f" --list-versions={list_versions}"
    else:
        command += " --download"
        if version:
            command += f" --version='{version}'"

        if 'caddy' not in exclude:
            caddy_data_directory_exists = config["ENABLE_WEB_PROXY"]
            if not caddy_data_directory_exists:
                exclude = (*exclude, "caddy")

        for service in exclude:
            command += f" --exclude={service}"

    job_runner = K8sTaskRunner(context.root, config)
    job_runner.run_task(service="backup-restore", command=command)


# Add the "templates" folder as a template root
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    str(importlib_resources.files("tutorbackup") / "templates")
)
# Render the "build" and "apps" folders
hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    [
        ("backup/build", "plugins"),
        ("backup/apps", "plugins"),
    ],
)
# Load patches from files
for path in glob(str(
        importlib_resources.files("tutorbackup") / "patches" / "*")):

    with open(path, encoding="utf-8") as patch_file:
        hooks.Filters.ENV_PATCHES.add_item(
            (os.path.basename(path), patch_file.read())
        )
# Add configuration entries
hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        (f"BACKUP_{key}", value)
        for key, value in config.get("defaults", {}).items()
    ]
)
hooks.Filters.CONFIG_UNIQUE.add_items(
    [
        (f"BACKUP_{key}", value)
        for key, value in config.get("unique", {}).items()
    ]
)
hooks.Filters.CONFIG_OVERRIDES.add_items(
    list(config.get("overrides", {}).items())
)
