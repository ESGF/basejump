# BASEJumper

A small web app for interfacing with HPSS in an automatic fashion.

## Architecture

BASEJumper consists of two parts; a web app frontend and a data transfer daemon in the back. BASEJumper is intended to be strictly an API; it only returns JSON responses to be consumed by CoG for displaying some insight into the workings of the daemon (for progress updates, etc). Dependencies are kept to a minimum, to facilitate a simple installation process. Pieces are kept very modular to allow flexible installations.

## Installation

To install, git clone this repo and then do the following commands:

```
$ virtualenv env
$ source env/bin/activate
$ pip install -r requirements.txt
```

Once you've got the requirements installed, you should just have to set up the basic configuration.

## Config

A configuration file is required. It can be located anywhere on your system, but if you're going to use either of the bundled commands (`mkdb.py` and `run.py`), you'll have to provide a "-c" or "--config" option with the path to the script (`./mkdb.py --config /path/to/my/config.py`).

Here's a simple config example. Each variable must be present and assigned an empty dictionary at the minimum (`db_config` is mandatory and be set up with a type or a url).

```python
import logging

# Configurations for python's logging module
log_config = {
	"filename": "/var/log/basejump.log",
	"level": logging.INFO
}

# Configurations for sqlalchemy
db_config = {
	"type": "sqlite",
	"url": "/opt/db/basejump.db"
}

# Configurations for flask
app_config = {
}

# No keys currently used
daemon_config = {	
}
```

Once you've got the config created, you need to create your database.

```
$ ./mkdb.py
```

If you have placed your `config.py` file in a custom location, you can pass the path to it using `-c` or `--config`.

## Running

After the configuration is done and the database is created, you can run the app and the daemon using the `run.py` script:

```
$ ./run.py
```

Again, if you have a custom config file location, you can pass it in using `-c` or `--config`.

This script isn't super well-suited to production use; it uses the built-in flask server. For optimal performance, you'll have to manually set up a WSGI script that does something to this effect:

```python
import basejumper.app
import args
application = basejumper.app.configure(args.config)
```
