from .__about__ import __version__
from glob import glob
import os
import pkg_resources
import click
from tutor import config as tutor_config
from tutor.commands.local import local as local_command_group


templates = pkg_resources.resource_filename(
    "tutorbackup", "templates"
)

config = {
    "defaults": {
        "VERSION": __version__,
        "DOCKER_IMAGE": "{{ DOCKER_REGISTRY }}backup:{{ BACKUP_VERSION }}",  # noqa: E501
    }
}

hooks = {
    "build-image": {
        "backup": "{{ BACKUP_DOCKER_IMAGE }}",
    },
    "remote-image": {
        "backup": "{{ BACKUP_DOCKER_IMAGE }}",
    },
}


@local_command_group.command(help="Backup MySQL, MongoDB, and Caddy")
@click.pass_obj
def backup(context):
    config = tutor_config.load(context.root)
    job_runner = context.job_runner(config)
    job_runner.run_job(
        service="backup",
        command="bash backup_local_services.sh"
    )


@local_command_group.command(help="Restore MySQL, MongoDB, and Caddy")
@click.pass_obj
def restore(context):
    config = tutor_config.load(context.root)

    filename = context.root + "/env/backup/backup.tar.xz"
    click.echo(f"Restoring from '{filename}'")
    if not os.path.isfile(filename):
        click.echo(f"ERROR: '{filename}' not found!")
        return

    job_runner = context.job_runner(config)
    job_runner.run_job(
        service="backup",
        command="bash restore_local_services.sh"
    )


def patches():
    all_patches = {}
    patches_dir = pkg_resources.resource_filename(
        "tutorbackup", "patches"
    )
    for path in glob(os.path.join(patches_dir, "*")):
        with open(path) as patch_file:
            name = os.path.basename(path)
            content = patch_file.read()
            all_patches[name] = content
    return all_patches
