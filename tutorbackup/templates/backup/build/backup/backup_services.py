#!/usr/bin/env python

from subprocess import check_call

import click

import glob
import logging
import os
import shutil
import sys
import tarfile

ENV = os.environ

DUMP_DIRECTORY = '/data'

MYSQL_DUMPFILE = os.path.join(DUMP_DIRECTORY, 'mysql_dump.sql')
MONGODB_DUMPDIR = os.path.join(DUMP_DIRECTORY, 'mongodb_dump')
CADDY_DUMPDIR = os.path.join(DUMP_DIRECTORY, 'caddy')

TARFILE = '/backup/backup.tar.xz'

logger = logging.getLogger(__name__)


def mysqldump():
    user = ENV['MYSQL_ROOT_USERNAME']
    password = ENV['MYSQL_ROOT_PASSWORD']
    host = ENV['MYSQL_HOST']
    port = ENV['MYSQL_PORT']
    outfile = MYSQL_DUMPFILE

    logger.info(f"Dumping MySQL databases on {host}:{port} to {outfile}")
    cmd = ("mysqldump "
           "--all-databases --single-transaction "
           "--quick --quote-names --max-allowed-packet=16M "
           f"--host={host} --port={port} "
           f"--user={user} --password={password}")
    with open(outfile, 'wb') as out:
        check_call(cmd,
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
    check_call(cmd,
               stdout=sys.stdout,
               stderr=sys.stderr)

    files = os.listdir(outdir)
    num_files = len(files)
    total_size = sum([os.path.getsize(f) for f in files])
    logger.info(f"Complete. {outdir} contains {num_files} file(s), "
                f"total size {total_size} bytes.")


def caddydump():
    outdir = CADDY_DUMPDIR

    logger.info(f"Copying Caddy data to {outdir}")
    shutil.copytree('caddy', outdir)

    files = [path for path in glob.glob(os.path.join(outdir, '**'))]
    num_files = len(files)
    total_size = sum([os.path.getsize(f) for f in files])
    logger.info(f"Complete. {outdir} contains {num_files} file(s), "
                f"total size {total_size} bytes.")


def archive():
    paths = [MYSQL_DUMPFILE, MONGODB_DUMPDIR, CADDY_DUMPDIR]
    outfile = TARFILE

    logger.info(f"Creating archive {outfile}")
    with tarfile.open(outfile, "w:xz") as tar:
        for item in paths:
            tar.add(item)

    size = os.path.getsize(outfile)
    logger.info(f"Complete. {outfile} is {size} bytes.")


def upload():
    from .s3_client import S3_CLIENT

    bucket = ENV['S3_BUCKET_NAME']
    file_name = TARFILE

    logger.info(f"Uploading {file_name} to S3 bucket {bucket}")
    S3_CLIENT.upload_file(
        file_name,
        bucket,
        os.path.basename(file_name),
    )
    # FIXME: Apparently: upload_file() doesn't return anything useful
    # in the response. It either succeeds, or fails and throws an
    # exception. We probably want to fetch some object metadata after
    # the upload, to check for a size match.
    logger.info("Complete.")


@click.command()
@click.option('--upload', is_flag=True, help="Upload to S3")
def main(upload):
    loglevel = logging.INFO
    try:
        loglevel = getattr(logging, ENV['LOG_LEVEL'].upper())
    except KeyError:
        pass
    logger.setLevel(loglevel)

    mysqldump()
    mongodump()
    caddydump()
    archive()

    if upload:
        upload()


if __name__ == '__main__':
    main()
