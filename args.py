import argparse
import os
import sys
import importlib

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", action="store", metavar="config", nargs=1, default=["config.py"])
vals = parser.parse_args()


def get_config_module(config_path):
	if "/" in config_path:
		# Make sure conifg path is on the sys path
		dirname, basename = os.path.split(config_path)
		root, ext = os.path.splitext(basename)
		if not os.path.exists(config_path):
			raise ValueError("Config file not found at %s" % config_path)
		if ext != ".py":
			raise ValueError("Config file must be a python module")
		if dirname not in sys.path:
			# Add to the path
			sys.path.append(dirname)
			return importlib.import_module(root)
	else:
		root, ext = os.path.splitext(config_path)
		if not os.path.exists(config_path):
			# Check if there's no extension
			if ext != "" or not os.path.exists(root + ".py"):
				raise ValueError("Config file not found at %s" % config_path)
		else:
			if ext != ".py":
				raise ValueError("Config file must be a python module")
		return importlib.import_module(root)

config = get_config_module(vals.config[0])
