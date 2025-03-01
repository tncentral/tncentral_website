workers = 3
#bind = 'tncentral.local:8000'
bind = 'tncentral.local:8000'
umask = 0o007
reload = True


#logging
loglevel = 'debug' # if not provided, 'info' is the default
accesslog = 'logs/access.log'
errorlog = 'logs/error.log'

# capture standard output to error.log file
capture_output = True

# ssl configuration
certfile = '/etc/letsencrypt/live/tncentral.local/fullchain.pem'
keyfile='/etc/letsencrypt/live/tncentral.local/privkey.pem'