from .__about__ import __version__
from glob import glob
import os
import pkg_resources
import click
from tutor import config as tutor_config
from tutor.commands.local import local as local_command_group
from tutor.commands.k8s import k8s as k8s_command_group, K8sJobRunner


templates = pkg_resources.resource_filename(
    "tutorbackup", "templates"
)

config = {
    "defaults": {
        "VERSION": __version__,
        "DOCKER_IMAGE": "{{ DOCKER_REGISTRY }}backup:{{ BACKUP_VERSION }}",  # noqa: E501
        "K8S_CRONJOB_HISTORYLIMIT_FAILURE": 1,
        "K8S_CRONJOB_HISTORYLIMIT_SUCCESS": 3,
        "K8S_CRONJOB_BACKUP_SCHEDULE": "0 0 * * *",
        "K8S_CRONJOB_RESTORE_SCHEDULE": None,
        "S3_HOST": "{{ S3_HOST | default('') }}",
        "S3_PORT": "{{ S3_PORT | default('') }}",
        "S3_REGION_NAME": "{{ S3_REGION | default('') }}",
        "S3_SIGNATURE_VERSION": "{{ S3_SIGNATURE_VERSION | default('s3v4') }}",
        "S3_ADDRESSING_STYLE": "{{ S3_ADDRESSING_STYLE | default('auto') }}",
        "S3_USE_SSL": "{{ S3_USE_SSL | default('True') }}",
        "S3_ACCESS_KEY": "{{ OPENEDX_AWS_ACCESS_KEY }}",
        "S3_SECRET_ACCESS_KEY": "{{ OPENEDX_AWS_SECRET_ACCESS_KEY }}",
        "S3_BUCKET_NAME": "backups",
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
        command="bash backup_services.sh"
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
        command="bash restore_services.sh"
    )


@k8s_command_group.command(help="Backup MySQL, MongoDB, and Caddy")
@click.pass_obj
def backup(context):  # noqa: F811
    config = tutor_config.load(context.root)
    job_runner = K8sJobRunner(context.root, config)
    command = "/bin/bash -c backup_services.sh && python upload_to_s3.py"
    job_runner.run_job(service="backup-restore", command=command)


@k8s_command_group.command(help="restore MySQL, MongoDB, and Caddy")
@click.pass_obj
@click.option('--version', default="", type=str,
              help="Version ID of the backup file")
def restore(context, version):  # noqa: F811
    config = tutor_config.load(context.root)
    job_runner = K8sJobRunner(context.root, config)
    command = f"/bin/bash -c python download_from_s3 {version} " \
              f"&& restore_services.sh"
    job_runner.run_job(service="backup-restore", command=command)


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
