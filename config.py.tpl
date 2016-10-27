import logging
log_config = {
    "filename": "/var/log/bjump.log"
    "level": logging.INFO
}

db_config = {
    "type": "sqlite",
    "url": "/data/bjump.db"
}

cache_config = {
    "CACHE_DIR": "/data/cache_directory"
}

# This is passed directly to flask, so it supports all standard flask configurations
# It also supports some custom keys for BASEJumper
app_config = {
    "DEBUG": True,
    "BASEJUMP_KEY": "secretkey1",  # Custom to BASEJumper, used for signing requests between the daemon and the frontend
    "SECRET_KEY": "secretkey2",
    "USE_X_SENDFILE": True,  # Enable to do low-overhead file transfers when behind apache
    "AUTHORIZATION_SERVICE_ENDPOINT": "https://my.esgf.node.test/esg-orp/saml/soap/secure/authorizationService.htm"  # Custom to BASEJumper, used for authorizing retrievals
}


# Most setups will probably have the daemon and the frontend deployed separately.
# You use the BASEJUMP_FRONTEND_URL to point the daemon at the appropriate frontend
daemon_config = {
    "BASEJUMP_FRONTEND_URL": "http://my.bjump.frontend.test:8888"
    "BASEJUMP_KEY": "secretkey1",
    "CACHE_DIR": "/data/daemon_cache",
    "TRANSFER_CMD": "cp" # Any command available to execute the transfer. Expects two paths (the local and the remote) as arguments.
}

smtp_config = {
    "server": "smtp.myhost.com",  # Also supports user and password
    "from_address": "nospam@myhost.com",
    #"subject_format": "HPSS Transfer of File {filename} Complete",  # Default value
    #"message_format": "Your transfer of {filename} is complete. Please download from {download_url} within {guarantee} days. After that time has elapsed, the file may be deleted to make room for other transfers."
}

host_config = {
    "hostname": "my.bjump.frontend.test"
    "port": 8888
}

base_config = {
}

# If you're behind a corporate firewall the does SSL decoding, you can use the packaged code and these configs to make OpenID work properly.
"""
import fetcher
import openid.fetchers
f = fetcher.RequestsFetcher(no_verify=True)
openid.fetchers.setDefaultFetcher(f)
"""
