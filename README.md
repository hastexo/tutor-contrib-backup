# backup plugin for [Tutor](https://docs.tutor.overhang.io)

## Installation

    pip install git+https://github.com/hastexo/tutor-contrib-backup

## Usage
To enable this plugin, run:

    tutor plugins enable backup

Before starting Tutor, build the Docker image:

    tutor images build backup

To run a backup in the Tutor local deployment:

    tutor local backup

This creates a tar file containing a dump of the MySQL database,
a dump of the MongoDB database, and a copy of the Caddy data directory.

You can find the tar file under `$(tutor config printroot)/env/backup/`.

To restore MySQL, MongoDB, and Caddy from a previously-made backup tar file, in 
the Tutor local deployment:

    tutor local restore

This will look for the tar file under `$(tutor config printroot)/env/backup/`.

## License

This software is licensed under the terms of the AGPLv3.
