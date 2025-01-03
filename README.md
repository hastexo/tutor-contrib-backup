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

| Open edX release  | Tutor version      | Plugin branch | Plugin release |
|-------------------|--------------------|---------------|----------------|
| Lilac             | `>=12.0, <13`      | Not supported | Not supported  |
| Maple             | `>=13.2, <14`[^v1] | `maple`       | 0.3.x          |
| Nutmeg            | `>=14.0, <15`      | `nutmeg`      | 1.x.x          |
| Olive             | `>=15.0, <16`      | `olive`       | 2.x.x          |
| Palm              | `>=16.0, <17`      | `quince`      | `>=2.1.0, <4`  |
| Quince            | `>=17.0, <18`      | `quince`      | `>=3.1.0, <4`  |
| Redwood[^journal] | `>=18.0, <19`      | `main`        | `>=4`          |
| Sumac             | `>=19.0, <20`      | `main`        | `>=4.1.0`      |

[^v1]: For Open edX Maple and Tutor 13, you must run version 13.3.0 or later.
       That is because this plugin uses the Tutor v1 plugin API, [which was introduced with that release](https://github.com/overhangio/tutor/blob/master/CHANGELOG.md#v1320-2022-04-24).

[^journal]: Tutor 18 and Open edX Redwood included a [leap in MongoDB releases (from 4.4 to 7.0)](https://github.com/overhangio/tutor/releases/tag/v18.0.0).
            As a result of this change, the amount of disk space required by MongoDB during a database restore increased substantially (to about 3 times the size of the database).
            When upgrading to Tutor 18, you may need to expand your MongoDB container's database storage volume.

## Installation

    pip install git+https://github.com/hastexo/tutor-contrib-backup@v4.1.0

## Usage

To enable this plugin, run:

    tutor plugins enable backup

Then, run the following command to add the plugin's configuration 
parameters to your Tutor environment:

    tutor config save

### Building the image

In order to build and push the local image, you will need to point your Docker image build process to a local registry.

You can do this in one of two ways:

1. You already set the Tutor `DOCKER_REGISTRY` option.
   In this case, this plugin will push the `backup` image to your previously configured registry.
2. You override just the `BACKUP_DOCKER_IMAGE` configuration value, for example:
   ```
   tutor config save --set BACKUP_DOCKER_IMAGE=localhost:5000/backup:v4.1.0
   ```
   Substitute the correct registry prefix if, rather than using a local instance of the [Distribution Registry](https://github.com/distribution/distribution), you are using a container registry provided by [GitHub](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry), [GitLab](https://docs.gitlab.com/ee/user/packages/container_registry/), [Harbor](https://goharbor.io/), etc.

Then, build the Docker image:

    tutor images build backup

And finally, push it to your local registry:

    tutor images push backup

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

If you are running Kubernetes in a production environment, you might need to store the 
dump and tar files in a [generic ephemeral volume](https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/#generic-ephemeral-volumes) instead of the default local node storage
(requires Kubernetes 1.23 or higher). To accomplish this, set `BACKUP_K8S_USE_EPHEMERAL_VOLUMES` to `True`.
Optionally you can change the volume size using the `BACKUP_K8S_EPHEMERAL_VOLUME_SIZE`
variable, which is `10Gi` by default.


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

## Configuration

### General options

* `BACKUP_DOCKER_IMAGE` (default: `<DOCKER_REGISTRY>backup:v4.1.0`, relative to `DOCKER_REGISTRY` as defined by the global Tutor option)

### Kubernetes options

* `BACKUP_K8S_CRONJOB_HISTORYLIMIT_FAILURE` (default: `1`)
* `BACKUP_K8S_CRONJOB_HISTORYLIMIT_SUCCESS` (default: `3`)
* `BACKUP_K8S_CRONJOB_STARTING_DEADLINE_SECONDS` (default: `900`)
* `BACKUP_K8S_CRONJOB_BACKUP_ENABLE` (default: `true`, periodic backup is enabled.)
* `BACKUP_K8S_CRONJOB_BACKUP_SCHEDULE` (default: `"0 0 * * *"`, once a day at midnight)
* `BACKUP_K8S_CRONJOB_RESTORE_ENABLE` (default: `false`, periodic restore is disabled.)
* `BACKUP_K8S_CRONJOB_RESTORE_SCHEDULE` (default: `"30 0 * * *"`, once a day at 30 mins past
   midnight)
* `BACKUP_K8S_CRONJOB_CONCURRENCYPOLICY` (default: `"Forbid"`, see [the Kubernetes documentation](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/#concurrency-policy) for other available options)
* `BACKUP_K8S_USE_EPHEMERAL_VOLUMES` (default: `false`)
* `BACKUP_K8S_EPHEMERAL_VOLUME_SIZE` (default: `10Gi`)

Make sure the periodic backup job always runs before the restore job during the 
day.

### Options related to S3 storage

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
* When dealing with very large databases, restoring MongoDB may consume more memory than available and the process may break.
  In this situation, you can set `BACKUP_MONGORESTORE_ADDITIONAL_OPTIONS` to `-j 1` to 
  [limit the number of collections](https://www.mongodb.com/docs/v4.2/reference/program/mongorestore/#cmdoption-mongorestore-numparallelcollections)
  that are restored in parallel in order to save memory.

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

[^aurora]: There is a known limitation in [certain configurations of AWS Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/mysql_rds_import_binlog_ssl_material.html) in which an attempt to back up the internal `mysql` database will result in an error:
           ```
           mysqldump: Couldn't execute 'SHOW CREATE PROCEDURE rds_import_binlog_ssl_material': Failed to load routine mysql.rds_import_binlog_ssl_material. The table mysql.proc is missing, corrupt, or contains bad data.
           ```

In such cases, you can specify the MySQL databases you would like to
back up, using the `BACKUP_MYSQL_DATABASES` option. This option takes
a list of strings with the names of the databases, such as:

```yaml
BACKUP_MYSQL_DATABASES:
  - openedx
  - notes
  - ecommerce
  - discovery
```

Remember to include all databases used by
[edx-platform](https://github.com/openedx/edx-platform), as well as
those created by any plugins installed.

You may or may not choose to include the internal `mysql` database in
this list. If you have made sure that all your database users and
privileges are managed by Tutor (as you should), and none have been
created manually, then it should be safe to not include `mysql` in the
`BACKUP_MYSQL_DATABASES` list. However, if you omit
`BACKUP_MYSQL_DATABASES` from your configuration altogether, then the
plugin does include the `mysql` database in the backup.

For MongoDB databases, the corresponding configuration option is:

```yaml
BACKUP_MONGODB_DATABASES:
  - openedx
  - cs_comments_service
```

If your MongoDB instance uses an authentication database name other 
than `admin`, make sure you provide that with
`BACKUP_MONGODB_AUTHENTICATION_DATABASE`.

### Opting out of single-transaction backups and flushing logs

In certain cloud MySQL services, like AWS Aurora, it might be forbidden (even for the `root` user) to lock the database.
In these cases you might get errors like `Couldn't execute 'FLUSH TABLES WITH READ LOCK': Access denied for user`. 
This is caused by using the `single-transaction` option in MySQL dumps, and flushing logs after restoring.

To overcome these issues, you can set `BACKUP_MYSQL_SINGLE_TRANSACTION` and `BACKUP_MYSQL_FLUSH_LOGS` to `false`. 
Both values are `true` by default.
`BACKUP_MYSQL_SINGLE_TRANSACTION` controls the use of `--single-transaction` option in the `mysqldump` command, while `BACKUP_MYSQL_FLUSH_LOGS` enables or disables issuing `mysqladmin flush-logs` after restoring the database.

Please note that doing this will cause the MySQL database to be dumped without locking the tables, which might result in inconsistent backup archives.
If you set `BACKUP_MYSQL_FLUSH_LOGS` to `false`, we recommend to stop all services before starting the backup process.

## Using this plugin with service version upgrades

In general, you should be able to use this plugin even when you are
upgrading to a new MySQL, MongoDB, or Caddy version. This is something
that commonly happens as a result of a new Open edX/Tutor major
release.

However, you need to make sure that after restoring a backup from a
prior version, you run `tutor local init` or `tutor k8s init` in order
to ensure that any required in-place data modifications also rerun.

## Changelog

For a detailed breakdown of features and fixes in each release, please
see the [changelog](CHANGELOG.md).

## License

This software is licensed under the terms of the AGPLv3.
