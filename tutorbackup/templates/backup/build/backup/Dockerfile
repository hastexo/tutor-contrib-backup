FROM python:3.8-buster
ENV PYTHONUNBUFFERED 1
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-4.2.asc | gpg --dearmor | tee /usr/share/keyrings/mongodb-ce-archive-keyring.gpg && \
    echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-ce-archive-keyring.gpg] https://repo.mongodb.org/apt/debian buster/mongodb-org/4.2 main" | tee /etc/apt/sources.list.d/mongodb-org-4.2.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends default-mysql-client mongodb-org-tools && \
    mkdir data backup

COPY backup_local_services.sh .
COPY restore_local_services.sh .
