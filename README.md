# Backup plugin for Tutor

This is a plugin for [Tutor](https://docs.tutor.overhang.io) that
provides backup and restore functionality for MySQL, MongoDB, and
Caddy services in both local and Kubernetes Tutor deployments.

In a local deployment, you can run the backup from the command line.
The backups are stored as a single compressed tar file, named
`backup.YYYY-MM-DD.tar.xz`, in `$(tutor config
printroot)/env/backup/`. You can then copy the Tutor config root
folder to a new host and restore your Open edX environment with the
restore command.

In Kubernetes, the plugin runs the backup job as a
[CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
by default. You can also run the backup job from the command line.  In
both cases the backup tar file, named `backup.YYYY-MM-DD.tar.xz`, is
stored in an S3 bucket.  Then, in a new Kubernetes deployment, you can
use the restore command to restore your Open edX environment.  You can
even schedule the restore as a CronJob to periodically download the
latest backup and restore your environment. This can, for example, be
useful if you want to maintain a standby site for disaster recovery
purposes.

## Version compatibility matrix

You must install a supported release of this plugin to match the Open
edX and Tutor version you are deploying. If you are installing this
plugin from a branch in this Git repository, you must select the
appropriate one:

| Open edX release | Tutor version     | Plugin branch | Plugin release |
|------------------|-------------------|---------------|----------------|
| Lilac            | `>=12.0, <13`     | Not supported | Not supported  |
| Maple            | `>=13.2, <14`[^1] | `maple`       | 0.3.x          |
| Nutmeg           | `>=14.0, <15`     | `main`        | 1.x.x          |

[^1]: For Open edX Maple and Tutor 13, you must run version 13.2.0 or
    later. That is because this plugin uses the Tutor v1 plugin API,
    [which was introduced with that
    release](https://github.com/overhangio/tutor/blob/master/CHANGELOG.md#v1320-2022-04-24).

## Installation

    pip install git+https://github.com/hastexo/tutor-contrib-backup@v1.1.0

## Usage

To enable this plugin, run:

    tutor plugins enable backup

Then, run the following command to add the plugin's configuration 
parameters to your Tutor environment:

    tutor config save

Before starting Tutor, build the Docker image:

    tutor images build backup

### In a Tutor local deployment:

To run a backup in a local Tutor deployment:

    tutor local backup

This creates a tar file containing a dump of the MySQL database,
a dump of the MongoDB database, and a copy of the Caddy data directory.

You can find the tar file under `$(tutor config printroot)/env/backup/`.

To restore MySQL, MongoDB, and Caddy from a previously-made backup tar file:

    tutor local restore

This will look for the tar file under `$(tutor config printroot)/env/backup/`,
extracts the tar file, and restore the services from the backup files.

You can also exclude specific data from the restore. For example, if
you want to restore only MySQL data, and leave the state of MongoDB
and Caddy untouched, run:

    tutor local restore --exclude=caddy --exclude=mongodb

### In a Tutor k8s deployment:

By default, the backup job runs as a scheduled 
[CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
once a day at midnight. You can change the schedule by changing the 
`BACKUP_K8S_CRONJOB_BACKUP_SCHEDULE` configuration parameter. To suspend 
the scheduled backup job, set `BACKUP_K8S_CRONJOB_BACKUP_ENABLE` to `false`. 
Note that you need to restart your Kubernetes deployment with 
`tutor k8s quickstart` for this change to take effect.

If you need to run the backup job outside the schedule, use:

    tutor k8s backup

The backup job backs up MySQL, MongoDB, and the Caddy data directory, 
creates a tar file with a date stamp, and uploads it to an S3 storage bucket as 
set by the `BACKUP_S3_*` configuration parameters. Note that if you want to 
run multiple backups in a day, you might want to enable
[object versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
 in your bucket. Otherwise, only the last backup taken on any day survives.

You might also consider applying a lifecyle [expiration
rule](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html)
to your storage bucket if you want to retain your backups for a
limited time, and discard backups beyond a certain age.

To restore from the latest version of the backup made today:

    tutor k8s restore

To restore from the latest version of the backup made on a particular date:

    tutor k8s restore --date={YYYY-MM-DD}

To restore from a particular version of the backup, you first need its 
version ID. You can either look this up by interacting with your S3 
bucket through your S3 provider's CLI or web UI; or you can use the 
command below to list the version ID and the corresponding timestamp of the 
last 20 backups:

    tutor k8s restore --list-versions

You can change the number of versions shown by passing an integer to the 
`list-versions` argument. For example, `--list-versions=10`.
This will start a Kubernetes Job. So the output will be in the corresponding 
pod's log.

Use the ID of the desired backup version to restore services:

    tutor k8s restore --version={version-id}

If you run multiple backups each day and want to restore from a specific 
version of a backup on a particular day, use `--version` in 
combination with `--date`.

The restore command will start a job that downloads the specified version of 
the backup from the S3 storage bucket and restores MySQL, MongoDB, and Caddy 
from it.

You can also exclude specific data from the restore. For example, if
you want to restore MySQL and MongoDB data, but not certificate data
for Caddy, run:

    tutor k8s restore --exclude=caddy

If you want to restore your environment periodically, set the 
`BACKUP_K8S_CRONJOB_RESTORE_ENABLE` configuration parameter to `true` and provide
the desired schedule by setting the `BACKUP_K8S_CRONJOB_RESTORE_SCHEDULE` 
(by default it is set to once a day at 30 mins past midnight).
This will always download the latest version of the backup from the S3 bucket. 
Note that you need to restart your Kubernetes deployment with `tutor k8s quickstart` 
for these changes to take effect.

You can also tweak the [history
limits](https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/#jobs-history-limits)
for the CronJobs using the `BACKUP_K8S_CRONJOB_HISTORYLIMIT_*` configuration 
parameters.

### A note on manual restores
The plugin does not stop services while restoring them. Before doing a manual 
(that is, not CronJob scheduled) restore, you might consider stopping the Caddy 
service or taking your site offline by other means. When the restore process is complete, 
remember to bring the Caddy service (or external load balancer or proxy) back online.
This prevents your users from encountering errors during the restore process.

Configuration
-------------

* `BACKUP_K8S_CRONJOB_HISTORYLIMIT_FAILURE` (default: `1`)
* `BACKUP_K8S_CRONJOB_HISTORYLIMIT_SUCCESS` (default: `3`)
* `BACKUP_K8S_CRONJOB_STARTING_DEADLINE_SECONDS` (default: `900`)
* `BACKUP_K8S_CRONJOB_BACKUP_ENABLE` (default: `true`, periodic backup is enabled.)
* `BACKUP_K8S_CRONJOB_BACKUP_SCHEDULE` (default: `"0 0 * * *"`, once a day at midnight)
* `BACKUP_K8S_CRONJOB_RESTORE_ENABLE` (default: `false`, periodic restore is disabled.)
* `BACKUP_K8S_CRONJOB_RESTORE_SCHEDULE` (default: `"30 0 * * *"`, once a day at 30 mins past
   midnight)

Make sure the periodic backup job always runs before the restore job during the 
day.

The following parameters will be pre-populated if the 
[tutor-contrib-s3](https://github.com/hastexo/tutor-contrib-s3) 
plugin is enabled in your Tutor deployment. If you don't have that 
plugin enabled, or you prefer to use a different S3 service or setting for 
your backup storage, change these configuration parameters:

* `BACKUP_S3_HOST` (default: `None`) - set only if using any other service than AWS S3
* `BACKUP_S3_PORT` (default: `None`) - set only if using any other service than AWS S3
* `BACKUP_S3_REGION` (default: `""`)
* `BACKUP_S3_SIGNATURE_VERSION` (default: `"s3v4"`)
* `BACKUP_S3_ADDRESSING_STYLE` (default: `"auto"`)
* `BACKUP_S3_USE_SSL` (default: `true`)
* `BACKUP_S3_ACCESS_KEY` (default: `"{{ OPENEDX_AWS_ACCESS_KEY }}"`)
* `BACKUP_S3_SECRET_ACCESS_KEY` (default: `"{{ OPENEDX_AWS_SECRET_ACCESS_KEY }}"`)
* `BACKUP_S3_BUCKET_NAME` (default: `"backups"`)

These values can be modified with `tutor config save --set
PARAM_NAME=VALUE` commands.

Depending on the nature and configuration of your S3-compatible
service, some of these values may be required to set.

* If using AWS S3, you will need to set `BACKUP_S3_REGION` to a non-empty value. 
  And make sure `BACKUP_S3_ADDRESSING_STYLE` is set to `"auto"`.
* If you want to use an alternative S3-compatible service, you need to set the 
  `BACKUP_S3_HOST` and `BACKUP_S3_PORT` parameters.
* For a Ceph Object Gateway that doesn’t set
  [rgw_dns_name](https://docs.ceph.com/en/latest/radosgw/config-ref/#confval-rgw_dns_name),
  you will need `BACKUP_S3_ADDRESSING_STYLE: path`.

### Selecting databases to backup

By default, all MySQL and MongoDB databases will be included in the 
backup. This is the desired behavior in most cases.

However, in some situations it may be necessary to explicitly choose
which databases must be included in the backup. For example, when the
same database cluster is used for other purposes and holds logical
databases for other services, you might not want to backup all
databases. In addition, if you are using a cloud provider database as
a service, the cluster may include internal databases that the LMS
user might not be allowed to access, thus throwing an error
during the backup process.[^aurora]

[^aurora]: There is a known limitation in [certain configurations of
  AWS
  Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/mysql_rds_import_binlog_ssl_material.html)
  in which an attempt to back up the internal `mysql` database will
  result in an error: `mysqldump: Couldn't execute 'SHOW CREATE
  PROCEDURE rds_import_binlog_ssl_material': Failed to load routine
  mysql.rds_import_binlog_ssl_material. The table mysql.proc is
  missing, corrupt, or contains bad data.`

In such cases, you can specify the MySQL and MongoDB databases you would like
to back up, using the `BACKUP_MYSQL_DATABASES` and `BACKUP_MONGODB_DATABASES` 
settings. These settings take a list of strings with the names of the 
databases, such as:

```yaml
BACKUP_MYSQL_DATABASES:
  - edxapp
  - notes
  - ecommerce
  - discovery
```

```yaml
BACKUP_MONGODB_DATABASES:
  - openedx
  - cs_comments_service
```

Remember to include all databases used by
[edx-platform](https://github.com/openedx/edx-platform), as well as
those created by any plugins installed.

If your MongoDB instance uses an authentication database name other 
than `admin`, make sure you provide that with
`BACKUP_MONGODB_AUTHENTICATION_DATABASE`.

## Changelog

For a detailed breakdown of features and fixes in each release, please
see the [changelog](CHANGELOG.md).

## License

This software is licensed under the terms of the AGPLv3.
