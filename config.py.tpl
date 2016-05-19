import logging
log_config = {
    "filename": "/var/log/basejump.log",
    "level": logging.INFO
}

db_config = {
    "type": "sqlite",
    "url": "/data/basejump.db"
}

# This is passed directly to flask, so it supports all standard flask configurations
# It also supports some custom keys for BASEJumper
app_config = {
    "DEBUG": True,
    "BASEJUMP_KEY": "",  # Custom to BASEJumper, used for signing requests between the daemon and the frontend
    "SECRET_KEY": "",
    "USE_X_SENDFILE": True,  # Enable to do low-overhead file transfers when behind apache
    "AUTHORIZATION_SERVICE_ENDPOINT": "https://pcmdi11.llnl.gov/esg-orp/saml/soap/secure/authorizationService.htm"  # Custom to BASEJumper, used for authorizing retrievals
}


daemon_config = {
}

smtp_config = {
    "server": "smtp.yourdomain.com",  # Also supports user and password
    "from_address": "nospam@yourdomain.com",
    #"subject_format": "HPSS Transfer of File {filename} Complete",  # Default value
    #"message_format": "Your transfer of {filename} is complete. Please download from {download_url} within {guarantee} days. After that time has elapsed, the file may be deleted to make room for other transfers."
}

host_config = {
    "hostname": "127.0.0.1",
    "port": 8080
}
