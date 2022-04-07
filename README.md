# Backup plugin for Tutor

This is an **experimental** plugin for
[Tutor](https://docs.tutor.overhang.io) that provides backup and restore 
functionality for MySQL, MongoDB, and Caddy services in both local and 
Kubernetes Tutor deployments.

In a local deployment, you can run the backup from the command line. 
The backups are stored as a single tar file in
`$(tutor config printroot)/env/backup/`. You can then copy the Tutor config root
folder to a new host and restore your Open edX environment with the restore 
command.

In Kubernetes, the plugin runs the backup job as a 
[CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) 
by default. You can also run the backup job from the command line.
In both cases the backup tar file is stored in an S3 bucket.
Then, in a new Kubernetes deployment, you can use the restore command to 
restore your Open edX environment. 
You can even schedule the restore as a CronJob to
periodically download the latest backup and restore your environment. This 
can, for example, be useful if you want to maintain a standby site for 
disaster recovery purposes.

## Installation

    pip install git+https://github.com/hastexo/tutor-contrib-backup@v0.0.2

## Usage

To enable this plugin, run:

    tutor plugins enable backup

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

    tutor k8s restore --exclude=caddy --exclude=mongodb

### In a Tutor k8s deployment:

By default, the backup job runs as a scheduled 
[CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
once a day at midnight. You can change the schedule by changing the 
`BACKUP_K8S_CRONJOB_BACKUP_SCHEDULE` configuration parameter. To turn off 
the scheduled job completely, set `BACKUP_K8S_CRONJOB_BACKUP_SCHEDULE` to None. 
Note that you need to restart your Kubernetes deployment with 
`tutor k8s quickstart` for this change to take effect.

If you need to run the backup job outside the schedule, use:

    tutor k8s backup

The backup job backs up MySQL, MongoDB, and the Caddy data directory, 
creates a tar file, and uploads it to an S3 storage bucket as set by 
the `BACKUP_S3_*` configuration parameters. Note that the bucket must support 
[object versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html).


To restore from the latest version of the backup:

    tutor k8s restore

To restore from a particular version of the backup:

    tutor k8s restore --version={version-id}

The restore command will start a job that downloads the specified version of 
the backup from the S3 storage bucket and restores MySQL, MongoDB, and Caddy 
from it.

You can also exclude specific data from the restore. For example, if
you want to restore MySQL and MongoDB data, but not certificate data
for Caddy, run:

    tutor k8s restore --exclude=caddy

If you want to restore your environment periodically, set the 
`BACKUP_K8S_CRONJOB_RESTORE_SCHEDULE` configuration parameter. This will always 
download the latest version of the backup from the S3 bucket. Note that you 
need to restart your Kubernetes deployment with `tutor k8s quickstart` for this 
change to take effect.

You can also tweak the [history
limits](https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/#jobs-history-limits)
for the CronJobs using the `BACKUP_K8S_CRONJOB_HISTORYLIMIT_*` configuration 
parameters.

Configuration
-------------

* `BACKUP_K8S_CRONJOB_HISTORYLIMIT_FAILURE` (default `1`)
* `BACKUP_K8S_CRONJOB_HISTORYLIMIT_SUCCESS` (default `3`)
* `BACKUP_K8S_CRONJOB_BACKUP_SCHEDULE` (default `"0 0 * * *"`, once a day at 
  midnight)
* `BACKUP_K8S_CRONJOB_RESTORE_SCHEDULE` (default `None`, periodic restore is 
  disabled)

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

## License

This software is licensed under the terms of the AGPLv3.
