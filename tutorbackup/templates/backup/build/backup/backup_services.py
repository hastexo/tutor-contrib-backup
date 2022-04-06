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


def mysqldump():
    user = ENV['MYSQL_ROOT_USERNAME']
    password = ENV['MYSQL_ROOT_PASSWORD']
    host = ENV['MYSQL_HOST']
    port = ENV['MYSQL_PORT']
    outfile = MYSQL_DUMPFILE

    logger.info(f"Dumping MySQL databases on {host}:{port} to {outfile}")
    cmd = ("mysqldump "
           "--all-databases --add-drop-database --routines "
           "--events --single-transaction "
           "--quick --quote-names --max-allowed-packet=16M "
           f"--host={host} --port={port} "
           f"--user={user} --password={password}")
    with open(outfile, 'wb') as out:
        check_call(cmd,
                   shell=True,
                   stdout=out,
                   stderr=sys.stderr)

    size = os.path.getsize(outfile)
    logger.info(f"Complete. {outfile} is {size} bytes.")


def mongodump():
    host = ENV['MONGODB_HOST']
    port = ENV['MONGODB_PORT']
    outdir = MONGODB_DUMPDIR

    logger.info(f"Dumping MongoDB databases on {host}:{port} to {outdir}")
    cmd = ("mongodump "
           f"--out={outdir} "
           f"--host={host} "
           f"--port={port}")
    try:
        cmd += (f" --username={ENV['MONGODB_USERNAME']} "
                f"--password={ENV['MONGODB_PASSWORD']}")
    except KeyError:
        pass

    check_call(cmd,
               shell=True,
               stdout=sys.stdout,
               stderr=sys.stderr)

    total_size = get_size(outdir)
    logger.info(f"Complete. {outdir} total size {total_size} bytes.")


def caddydump():
    outdir = CADDY_DUMPDIR
    logger.info(f"Copying Caddy data to {outdir}")
    shutil.copytree('caddy', outdir)

    total_size = get_size(outdir)
    logger.info(f"Complete. {outdir} total size {total_size} bytes.")


def archive(paths):
    outfile = TARFILE

    logger.info(f"Creating archive {outfile}")
    with tarfile.open(outfile, "w:xz") as tar:
        for item in paths:
            tar.add(item)

    size = os.path.getsize(outfile)
    logger.info(f"Complete. {outfile} is {size} bytes.")


def upload_to_s3():
    from s3_client import S3_CLIENT

    bucket = ENV['S3_BUCKET_NAME']
    file_name = TARFILE

    logger.info(f"Uploading {file_name} to S3 bucket {bucket}")
    try:
        S3_CLIENT.upload_file(
            file_name,
            bucket,
            os.path.basename(file_name),
        )
        logger.info(f"Uploaded {file_name} to {bucket}.")

        logger.info("Checking uploaded file's integrity ...")
        obj_metadata = S3_CLIENT.head_object(
            Bucket=bucket,
            Key=os.path.basename(file_name),
        )

        received_checksum = obj_metadata['ETag'].strip('"')
        calculated_checksum = hashlib.md5(
            open(file_name, 'rb').read()).hexdigest()
        version_id = obj_metadata['VersionId']
        size = obj_metadata['ContentLength']

        if received_checksum == calculated_checksum:
            logger.info(f"File integrity verified.\n"
                        f"Version ID: '{version_id}'\n"
                        f"Size: {size} bytes\n"
                        f"Checksum: '{received_checksum}'")
        else:
            S3_CLIENT.delete_object(
                Bucket=bucket,
                Key=os.path.basename(file_name),
                VersionId=version_id,
            )
            raise ClientError(
                msg=f"File integrity could not be verified. "
                    f"Deleted the uploaded version "
                    f"(VersionId: {version_id})."
            )

    except ClientError as e:
        logger.exception(e, exc_info=True)


@click.command()
@click.option(
    '--exclude',
    type=click.Choice(['mysql', 'mongodb', 'caddy']),
    multiple=True
)
@click.option('--upload', is_flag=True, help="Upload to S3")
def main(exclude, upload):
    loglevel = logging.INFO
    try:
        loglevel = getattr(logging, ENV['LOG_LEVEL'].upper())
    except KeyError:
        pass
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(loglevel)

    paths = []
    if 'mysql' not in exclude:
        mysqldump()
        paths.append(MYSQL_DUMPFILE)
    if 'mongodb' not in exclude:
        mongodump()
        paths.append(MONGODB_DUMPDIR)
    if 'caddy' not in exclude:
        caddydump()
        paths.append(CADDY_DUMPDIR)

    archive(paths)

    if upload:
        upload_to_s3()


if __name__ == '__main__':
    main()
