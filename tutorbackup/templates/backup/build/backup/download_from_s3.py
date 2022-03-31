import os
import sys
from botocore.exceptions import ClientError
from s3_client import S3_CLIENT


if __name__ == "__main__":
    try:
        version_id = sys.argv[1]
    except IndexError:
        version_id = None

    file_name = "/backup/backup.tar.xz"
    try:
        response = S3_CLIENT.download_file(
            os.environ['S3_BUCKET_NAME'],
            os.path.basename(file_name),
            file_name,
            ExtraArgs={'VersionId': version_id} if version_id else None,
        )
    except ClientError:
        raise
