## Version 1.0.0 (2022-08-04)

* [BREAKING CHANGE] Support Tutor 14 and Open edX Nutmeg. This entails
  a configuration format change from JSON to YAML, meaning that from
  version 1.0.0 this plugin only supports Tutor versions from 14.0.0
  (and with that, only Open edX versions from Nutmeg).

## Version 0.3.0 (2022-07-28)

* [feature] From this version forward the backup files contain a date
  stamp, and are thus named `backup.YYYY-MM-DD.tar.xz` rather than
  just `backup.tar.xz`. Users can now specify a date when using the
  restore command. In a Kubernetes deployment, if multiple backups are
  made in one day, users can specify the date and the version ID of
  the desired backup when restoring. If no date is specified on
  restore, the restore job looks for a backup from today. This means
  that when upgrading from an earlier version, attempting a restore
  operation *before any new backup is made* will fail because the
  restore will be looking for a backup named
  `backup.YYYY-MM-DD.tar.xz` when no such backup exists yet. In that
  event, please rename your existing `backup.tar.xz` file to the
  `backup.YYYY-MM-DD.tar.xz` format, reflecting the current date.

## Version 0.2.0 (2022-07-26)

* [feature] Add ability to enable and disable CronJobs by suspending them.
* [fix] Remove dependencies on mysql and mongodb from the
  docker-compose configuration if Tutor is configured to run with
  external MySQL and MongoDB.

## Version 0.1.0 (2022-06-29)

* [refactor] Use Tutor v1 plugin API

## Version 0.0.6 (2022-04-19)

* [feature] List available backup versions using `tutor k8s restore 
  --list-versions`.

## Version 0.0.5 (2022-04-13)

* [fix] Fix for k8s restore that would fail if no version ID was given.

## Version 0.0.4 (2022-04-12)

* [fix] When checking file integrity after download, compare the checksum to 
  the correct version of the backup file on S3.
* [feature] Add timestamps to log messages.

## Version 0.0.3 (2022-04-11)

* [fix] Don’t break on existing directories when restoring Caddy data.

## Version 0.0.2 (2022-04-07)

* [refactor] Rewrite backup and restore scripts in Python, improving
  logging and integrity verification.
* [feature] Add ability to exclude individual services from restore.

## Version 0.0.1 (2022-04-01)

**Experimental. Do not use in production.**

* Add backup and restore functionality for k8s Tutor deployment.
* Add backup and restore functionality for local Tutor deployment.
* Created plugin with
  [Cookiecutter](https://cookiecutter.readthedocs.io/) 
  from https://github.com/fghaas/cookiecutter-tutor-plugin.
