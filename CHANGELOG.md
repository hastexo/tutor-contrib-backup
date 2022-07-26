## Unreleased

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
