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

Once your application is configured, you'll need to run the daemon (`./basejumpd` should hopefully do the trick) and the web server (`./run.py`). Then you should be able to point your browser at wherever it's running.

The `run.py` script isn't super well-suited to production use; it uses the built-in flask server. For optimal performance, you'll have to manually set up a WSGI script that does something to this effect:

```python
import basejumper.app
import args
application = basejumper.app.configure(args.config)
```

and run it from some WSGI-compatible system (mod_wsgi, uwsgi, etc.).

# Installing Dependencies

You *should* be able to just do `pip install -r requirements.txt`. However, if you're on a mac, `m2crypto`, a dependency of `ndg_saml`, requires some manual intervention. See [this page](https://gitlab.com/m2crypto/m2crypto/blob/master/INSTALL.rst#macosx) on how to install `m2crypto`.

