#!/bin/bash
set -e
tar -xvf backup/backup.tar.xz
mysql --password=$MYSQL_ROOT_PASSWORD --user=$MYSQL_ROOT_USERNAME --host=$MYSQL_HOST --port=$MYSQL_PORT < data/mysql_dump.sql
mongorestore --host=$MONGODB_HOST --port=$MONGODB_PORT \
  {% if MONGODB_USERNAME and MONGODB_PASSWORD %}--username=$MONGODB_USERNAME --password=$MONGODB_PASSWORD {% endif %}--stopOnError /data/mongodb_dump/
if [ -d "/data/caddy" ]; then
  cp -r /data/caddy/* /caddy/
fi
