#!/usr/bin/env python

import logging
import os
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path
from subprocess import check_call

import click
from botocore.exceptions import ClientError

try:
    from distutils.util import strtobool  # pre-3.12
except ImportError:
    from setuptools.distutils.util import strtobool  # 3.12+

ENV = os.environ

DUMP_DIRECTORY = '/data'

MYSQL_DUMPFILE = os.path.join(DUMP_DIRECTORY, 'mysql_dump.sql')
MONGODB_DUMPDIR = os.path.join(DUMP_DIRECTORY, 'mongodb_dump')
CADDY_DUMPDIR = os.path.join(DUMP_DIRECTORY, 'caddy')

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
    flush_logs = bool(strtobool(ENV['MYSQL_FLUSH_LOGS']))
    dump_file = MYSQL_DUMPFILE

    logger.info(f"Restoring MySQL databases on {host}:{port} from {dump_file}")
    mysql_cmd = ("mysql "
                 f"--host={host} --port={port} "
                 f"--user={user} --password={password}")
    with open(dump_file, 'rb') as dump:
        check_call(mysql_cmd,
                   shell=True,
                   stdin=dump,
                   stdout=sys.stdout,
                   stderr=sys.stderr)
    logger.info("MySQL restored.")

    if flush_logs:
        logger.info(f"Flushing logs on {host}:{port}")
        mysqladmin_cmd = ("mysqladmin "
                          f"--host={host} --port={port} "
                          f"--user={user} --password={password} "
                          "flush-logs")
        check_call(mysqladmin_cmd,
                   shell=True,
                   stdout=sys.stdout,
                   stderr=sys.stderr)
        logger.info("Logs flushed.")


def restore_mongodb():
    host = ENV['MONGODB_HOST']
    port = ENV['MONGODB_PORT']
    dump_dir = MONGODB_DUMPDIR

    logger.info(
        f"Restoring MongoDB databases on {host}:{port} from {dump_dir}")
    cmd = ("mongorestore "
           "--stopOnError --drop "
           f"--host={host} --port={port} "
           f"{ENV['MONGORESTORE_ADDITIONAL_OPTIONS']} "
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


def extract(file_name):
    out_dir = DUMP_DIRECTORY

    logger.info(f"Extracting archive {file_name} to {out_dir}")
    try:
        with tarfile.open(file_name, "r:xz") as tar:
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner) 
                
            
            safe_extract(tar)
    except FileNotFoundError as e:
        logger.exception(e, exc_info=True)
        raise e

    size = get_size(out_dir)
    logger.info(f"Complete. {out_dir} is {size} bytes.")


def download_from_s3(file_name, version_id=None):
    from s3_client import S3_CLIENT, IntegrityError, calculate_checksum

    # Create the subdirectories to the tar file
    outfile_path = os.path.dirname(file_name)
    if outfile_path:
        Path(outfile_path).mkdir(parents=True, exist_ok=True)

    bucket = ENV['S3_BUCKET_NAME']

    logger.info(f"Downloading {file_name} from S3 bucket {bucket}")
    try:
        S3_CLIENT.download_file(
            bucket,
            os.path.basename(file_name),
            file_name,
            ExtraArgs={'VersionId': version_id} if version_id else None,
        )

        logger.info("Checking downloaded file's integrity ...")
        # boto3.client.head_object will break if empty string or None values
        # are passed as the VersionId argument. So add that function argument
        # only if a version ID is given.
        if version_id:
            obj_metadata = S3_CLIENT.head_object(
                Bucket=bucket,
                Key=os.path.basename(file_name),
                VersionId=version_id,
            )
        else:
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
        calculated_checksum = calculate_checksum(file_name)
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
        raise e


def get_versions(file_name, number_of_versions=20):
    from s3_client import S3_CLIENT

    bucket = ENV['S3_BUCKET_NAME']

    logger.info(
        f"Retrieving available versions for {file_name} from {bucket}")
    try:
        response = S3_CLIENT.list_object_versions(
            Bucket=bucket,
            Prefix=os.path.basename(file_name),
        )
        column_width = 32
        output = (f"{'VersionId'.center(column_width)}  "
                  f"{'Timestamp'.center(column_width)}\n")
        for item in response['Versions'][:number_of_versions]:
            output += f"{item['VersionId']}  {item['LastModified']}\n"

        logger.info(f"Last {number_of_versions} backup versions:\n"
                    f"{output}")

    except ClientError as e:
        logger.exception(e, exc_info=True)
        raise e


@click.command()
@click.option(
    '--exclude',
    type=click.Choice(['mysql', 'mongodb', 'caddy']),
    multiple=True
)
@click.option('--date', type=click.DateTime(formats=["%Y-%m-%d"]),
              default=str(datetime.today().date()),
              help="Backup date (YYYY-MM-DD)")
@click.option('--version', default="", type=str,
              help="Version ID of the backup file")
@click.option('--download', is_flag=True, help="Download from S3")
@click.option('--list-versions', is_flag=False, flag_value=20, type=int,
              help="List n latest backup versions (n=20 by default)")
def main(exclude, date, version, download, list_versions):
    loglevel = logging.INFO
    try:
        loglevel = getattr(logging, ENV['LOG_LEVEL'].upper())
    except KeyError:
        pass
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(loglevel)

    file_name = f'/data/backup/backup.{date.date()}.tar.xz'

    if list_versions:
        get_versions(file_name, number_of_versions=list_versions)
        return

    if download:
        download_from_s3(file_name, version_id=version)

    extract(file_name)

    if 'mysql' not in exclude:
        restore_mysql()
    if 'mongodb' not in exclude:
        restore_mongodb()
    if 'caddy' not in exclude:
        restore_caddy()


if __name__ == '__main__':
    main()
