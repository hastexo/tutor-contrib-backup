#!/bin/bash
set -e
tar -xvf backup/backup.tar.xz
mysql --password=$MYSQL_ROOT_PASSWORD --user=$MYSQL_ROOT_USERNAME --host=$MYSQL_HOST --port=$MYSQL_PORT < data/mysql_dump.sql
mongorestore --host=$MONGODB_HOST --port=$MONGODB_PORT --stopOnError /data/mongodb_dump/
cp -r /data/caddy/* /caddy/
