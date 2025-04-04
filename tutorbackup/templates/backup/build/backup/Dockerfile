FROM {{ BACKUP_BASE_IMAGE }}
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y curl gnupg
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor > /usr/share/keyrings/mongodb-ce-archive-keyring.gpg && \
    echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-ce-archive-keyring.gpg] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends mysql-client-8.0 mongodb-org-tools python3-pip python3-venv python-is-python3
RUN python3 -m venv /s3/venv/
ENV PATH "/s3/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install boto3 click && \
    mkdir data backup

COPY backup_services.py .
COPY restore_services.py .
COPY s3_client.py .

