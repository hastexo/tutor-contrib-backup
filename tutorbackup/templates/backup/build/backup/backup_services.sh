#!/bin/bash
set -e
mysqldump --all-databases --single-transaction --quick --quote-names --max-allowed-packet=16M \
  --password=$MYSQL_ROOT_PASSWORD --user=$MYSQL_ROOT_USERNAME --host=$MYSQL_HOST --port=$MYSQL_PORT > /data/mysql_dump.sql
mongodump --out=/data/mongodb_dump --host=$MONGODB_HOST \
  --port=$MONGODB_PORT {% if MONGODB_USERNAME and MONGODB_PASSWORD %}--username=$MONGODB_USERNAME --password=$MONGODB_PASSWORD{% endif %}
if [ -d "caddy" ]; then
  cp -r caddy/ data/
fi
tar --exclude='/data/caddy/locks' -Jcvf /backup/backup.tar.xz /data/
