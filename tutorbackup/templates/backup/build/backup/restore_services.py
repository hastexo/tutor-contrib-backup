#!/usr/bin/env python

import hashlib
import logging
import os
import shutil
import sys
import tarfile
from subprocess import check_call

import click
from botocore.exceptions import ClientError


ENV = os.environ

DUMP_DIRECTORY = '/data'

MYSQL_DUMPFILE = os.path.join(DUMP_DIRECTORY, 'mysql_dump.sql')
MONGODB_DUMPDIR = os.path.join(DUMP_DIRECTORY, 'mongodb_dump')
CADDY_DUMPDIR = os.path.join(DUMP_DIRECTORY, 'caddy')

TARFILE = '/backup/backup.tar.xz'

logger = logging.getLogger(__name__)


def get_size(dir_path):
    total_size = os.path.getsize(dir_path)
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        if os.path.isfile(item_path) and not os.path.islink(item_path):
            total_size += os.path.getsize(item_path)
        elif os.path.isdir(item_path):
            total_size += get_size(item_path)
    return total_size


def restore_mysql():
    user = ENV['MYSQL_ROOT_USERNAME']
    password = ENV['MYSQL_ROOT_PASSWORD']
    host = ENV['MYSQL_HOST']
    port = ENV['MYSQL_PORT']
    dump_file = MYSQL_DUMPFILE

    logger.info(f"Restoring MySQL databases on {host}:{port} from {dump_file}")
    cmd = ("mysql "
           f"--host={host} --port={port} "
           f"--user={user} --password={password}")
    with open(dump_file, 'rb') as dump:
        check_call(cmd,
                   shell=True,
                   stdin=dump,
                   stdout=sys.stdout,
                   stderr=sys.stderr)

    logger.info("MySQL restored.")


def restore_mongodb():
    host = ENV['MONGODB_HOST']
    port = ENV['MONGODB_PORT']
    dump_dir = MONGODB_DUMPDIR

    logger.info(
        f"Restoring MongoDB databases on {host}:{port} from {dump_dir}")
    cmd = ("mongorestore "
           "--stopOnError --drop "
           f"--host={host} --port={port} "
           f"{dump_dir}"
           )
    try:
        cmd += (f" --username={ENV['MONGODB_USERNAME']} "
                f"--password={ENV['MONGODB_PASSWORD']}")
    except KeyError:
        pass

    check_call(cmd,
               shell=True,
               stdout=sys.stdout,
               stderr=sys.stderr)

    logger.info("MongoDB restored.")


def restore_caddy():
    dump_dir = CADDY_DUMPDIR
    caddy_dir = 'caddy'
    logger.info(f"Copying Caddy data from {dump_dir}")
    shutil.copytree(dump_dir, caddy_dir, dirs_exist_ok=True)

    total_size = get_size(caddy_dir)
    logger.info(f"Complete. {caddy_dir} total size {total_size} bytes.")


def extract():
    tar_file = TARFILE
    out_dir = DUMP_DIRECTORY

    logger.info(f"Extracting archive {tar_file} to {out_dir}")
    with tarfile.open(tar_file, "r:xz") as tar:
        tar.extractall()

    size = get_size(out_dir)
    logger.info(f"Complete. {out_dir} is {size} bytes.")


def download_from_s3(version_id=None):
    from s3_client import S3_CLIENT, IntegrityError

    bucket = ENV['S3_BUCKET_NAME']
    file_name = TARFILE

    logger.info(f"Downloading {file_name} from S3 bucket {bucket}")
    try:
        S3_CLIENT.download_file(
            bucket,
            os.path.basename(file_name),
            file_name,
            ExtraArgs={'VersionId': version_id} if version_id else None,
        )

        logger.info("Checking downloaded file's integrity ...")
        obj_metadata = S3_CLIENT.head_object(
            Bucket=bucket,
            Key=os.path.basename(file_name),
        )

        received_version_id = obj_metadata['VersionId']
        if version_id:
            version_id_correct = (version_id == received_version_id)
        else:
            version_id_correct = True

        received_checksum = obj_metadata['Metadata']['checksum-md5']
        calculated_checksum = hashlib.md5(
            open(file_name, 'rb').read()).hexdigest()
        checksum_correct = (received_checksum == calculated_checksum)

        size = os.path.getsize(file_name)

        if checksum_correct and version_id_correct:
            logger.info("File integrity verified.\n"
                        f"Version ID: '{received_version_id}'\n"
                        f"Size: {size} bytes\n"
                        f"Checksum: '{received_checksum}'")
        else:
            os.remove(file_name)
            raise IntegrityError(
                "File integrity could not be verified. "
                "Deleted the downloaded file with "
                f"VersionId='{received_version_id}'.")

    except (ClientError, IntegrityError) as e:
        logger.exception(e, exc_info=True)


@click.command()
@click.option(
    '--exclude',
    type=click.Choice(['mysql', 'mongodb', 'caddy']),
    multiple=True
)
@click.option('--version', default="", type=str,
              help="Version ID of the backup file")
@click.option('--download', is_flag=True, help="Download from S3")
def main(exclude, version, download):
    loglevel = logging.INFO
    try:
        loglevel = getattr(logging, ENV['LOG_LEVEL'].upper())
    except KeyError:
        pass
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(loglevel)

    if download:
        download_from_s3(version_id=version)

    extract()

    if 'mysql' not in exclude:
        restore_mysql()
    if 'mongodb' not in exclude:
        restore_mongodb()
    if 'caddy' not in exclude:
        restore_caddy()


if __name__ == '__main__':
    main()
