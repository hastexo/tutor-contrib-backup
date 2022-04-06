FROM python:3.8-buster
ENV PYTHONUNBUFFERED 1
RUN python3 -m venv /s3/venv/
ENV PATH "/s3/venv/bin:$PATH"

RUN curl -fsSL https://www.mongodb.org/static/pgp/server-4.2.asc | gpg --dearmor | tee /usr/share/keyrings/mongodb-ce-archive-keyring.gpg && \
    echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-ce-archive-keyring.gpg] https://repo.mongodb.org/apt/debian buster/mongodb-org/4.2 main" | tee /etc/apt/sources.list.d/mongodb-org-4.2.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends default-mysql-client mongodb-org-tools && \
    pip install --upgrade pip && \
    pip install boto3 click && \
    mkdir data backup

COPY backup_services.py .
COPY restore_services.sh .

COPY s3_client.py .
COPY download_from_s3.py .
