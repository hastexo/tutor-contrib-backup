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
