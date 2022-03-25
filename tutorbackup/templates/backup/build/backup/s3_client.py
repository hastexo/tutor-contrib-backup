import os
import boto3
from botocore.config import Config


config = Config(
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
    aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'],
    config=config,
)
