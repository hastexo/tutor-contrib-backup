#!/usr/bin/env python

import logging
import os
import shutil
import sys
import tarfile
from datetime import datetime
from subprocess import check_call, check_output, STDOUT, CalledProcessError
from pathlib import Path

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

date_stamp = datetime.today().strftime("%Y-%m-%d")
TARFILE = f'/data/backup/backup.{date_stamp}.tar.xz'

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
    single_transaction = bool(strtobool(ENV['MYSQL_SINGLE_TRANSACTION']))
    outfile = MYSQL_DUMPFILE
    dblist = []

    mysql_databases = ENV.get('MYSQL_DATABASES')
    if mysql_databases:
        databases_statement = f"--databases {mysql_databases}"
        logger.info(f"Dumping MySQL databases {mysql_databases} "
                    f"on {host}:{port} to {outfile}")
    else:
        sql_query="""SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN
             ('mysql', 'sys', 'performance_schema', 'information_schema')"""

        mysql_cmd = (f"mysql --host={host} --port={port} --user={user} --password={password} -BANe \"{sql_query}\" ")

        logger.info("Retrieving the list of database schemas to backup")
        try:
            dbout = check_output([mysql_cmd], stderr=STDOUT, timeout=5, shell=True, universal_newlines=True)
        except CalledProcessError as e:
            logger.error("MySQL Command Status : FAIL", e.returncode, e.output)
        else:
            # The element at position [0] is the following message, so we have to exclude it from the schemas list:
            # "mysql: [Warning] Using a password on the command line interface can be insecure."
            dblist = dbout.splitlines()[1:]

        databases = " ".join(dblist)

        databases_statement = f"--databases {databases}"
        logger.info(f"Dumping MySQL databases "
                    f"on {host}:{port} to {outfile}")

    cmd = ("mysqldump "
           f"{databases_statement} "
           "--add-drop-database --routines "
           "--events "
           "--quick --quote-names --max-allowed-packet=16M "
           f"--host={host} --port={port} "
           f"--user={user} --password={password}")

    if single_transaction:
        cmd += " --single-transaction"

    with open(outfile, 'wb') as out:
        check_call(cmd,
                   shell=True,
                   stdout=out,
                   stderr=sys.stderr)

    size = os.path.getsize(outfile)
    logger.info(f"Complete. {outfile} is {size} bytes.")


def get_mongodump_command(database=None):
    host = ENV['MONGODB_HOST']
    port = ENV['MONGODB_PORT']
    outdir = MONGODB_DUMPDIR

    cmd = ("mongodump "
           f"--out={outdir} "
           f"--host={host} "
           f"--port={port}")

    if database:
        cmd += f" --db={database}"

    try:
        cmd += (f" --username={ENV['MONGODB_USERNAME']} "
                f"--password={ENV['MONGODB_PASSWORD']} "
                "--authenticationDatabase="
                f"{ENV['MONGODB_AUTHENTICATION_DATABASE']}")
    except KeyError:
        pass

    return cmd


def mongodump():
    host = ENV['MONGODB_HOST']
    port = ENV['MONGODB_PORT']
    outdir = MONGODB_DUMPDIR
    mongodb_databases = ENV.get('MONGODB_DATABASES')

    if mongodb_databases:
        for database in mongodb_databases.split():
            logger.info(f"Dumping MongoDB database '{database}' "
                        f"on {host}:{port} to {outdir}.")
            cmd = get_mongodump_command(database)
            check_call(cmd,
                       shell=True,
                       stdout=sys.stdout,
                       stderr=sys.stderr)
    else:
        logger.info("Dumping all MongoDB databases "
                    f"on {host}:{port} to {outdir}.")
        cmd = get_mongodump_command()
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

    # Create the subdirectories to the tar file
    outfile_path = os.path.dirname(outfile)
    if outfile_path:
        Path(outfile_path).mkdir(parents=True, exist_ok=True)

    logger.info(f"Creating archive {outfile}")
    with tarfile.open(outfile, "w:xz") as tar:
        for item in paths:
            tar.add(item)

    size = os.path.getsize(outfile)
    logger.info(f"Complete. {outfile} is {size} bytes.")


def upload_to_s3():
    from s3_client import S3_CLIENT, IntegrityError, calculate_checksum

    bucket = ENV['S3_BUCKET_NAME']
    file_name = TARFILE

    logger.info(f"Calculating checksum for {file_name}")
    calculated_checksum = calculate_checksum(file_name)
    logger.info(f"Uploading {file_name} to S3 bucket {bucket}")
    try:
        S3_CLIENT.upload_file(
            file_name,
            bucket,
            os.path.basename(file_name),
            ExtraArgs={
                'Metadata': {'checksum-md5': calculated_checksum},
            }
        )
        logger.info(f"Uploaded {file_name} to {bucket}.")

        logger.info("Checking uploaded file's integrity ...")
        obj_metadata = S3_CLIENT.head_object(
            Bucket=bucket,
            Key=os.path.basename(file_name),
        )

        received_checksum = obj_metadata['Metadata']['checksum-md5']
        version_id = obj_metadata['VersionId']
        size = obj_metadata['ContentLength']

        if received_checksum == calculated_checksum:
            logger.info("File integrity verified.\n"
                        f"Version ID: '{version_id}'\n"
                        f"Size: {size} bytes\n"
                        f"Checksum: '{received_checksum}'")
        else:
            S3_CLIENT.delete_object(
                Bucket=bucket,
                Key=os.path.basename(file_name),
                VersionId=version_id,
            )
            raise IntegrityError(
                "File integrity could not be verified. "
                "Deleted the uploaded version "
                f"(VersionId: {version_id})."
            )

    except (ClientError, IntegrityError) as e:
        logger.exception(e, exc_info=True)
        raise e


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
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
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
