import hashlib
import os
import boto3
from botocore.config import Config


config = Config(
    request_checksum_calculation=os.environ['S3_REQUEST_CHECKSUM_CALCULATION'],
    signature_version=os.environ['S3_SIGNATURE_VERSION'],
    s3={
        'addressing_style': os.environ['S3_ADDRESSING_STYLE'],
    }
)

S3_CLIENT = boto3.client(
    service_name='s3',
    region_name=os.environ['S3_REGION_NAME'],
    use_ssl=os.environ['S3_USE_SSL'],
    endpoint_url=os.environ.get('S3_ENDPOINT_URL'),
    aws_access_key_id=os.environ['S3_ACCESS_KEY'],
    aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'],
    config=config,
)


class IntegrityError(BaseException):
    pass


def calculate_checksum(file_name):
    # To avoid reading in the whole file into memory, break it
    # down into chunks and calculate the checksum by updating
    # the md5 hash. The number of read bytes should be a
    # multiple of the hash algorithm's block size. Here we have
    # chosen 128 times MD5's block size (128). This results in
    # chunks of 16KiB. Values above this do not show a tangible
    # performance benefit.
    num_of_blocks = 128
    with open(file_name, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(num_of_blocks * file_hash.block_size):
            file_hash.update(chunk)
    return file_hash.hexdigest()
