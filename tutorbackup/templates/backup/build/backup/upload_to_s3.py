import os
from botocore.exceptions import ClientError
from s3_client import S3_CLIENT


if __name__ == "__main__":
    file_name = "/backup/backup.tar.xz"
    try:
        response = S3_CLIENT.upload_file(
            file_name,
            os.environ['S3_BUCKET_NAME'],
            os.path.basename(file_name),
        )
    except ClientError:
        raise
