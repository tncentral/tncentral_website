###
## This file will be called by the tncentral.service installed at
## '/etc/systemd/system/tncentral.service' - this service will run the gunicorn
## server as a service.
###
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_tn import create_app

app = create_app()

# If the application runs behind a proxy. This is necessary if gunicorn 
# is running under apache
if app.config['BEHIND_PROXY']:
    app.wsgi_app = ProxyFix(
        # app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

if __name__ == '__main__':
    app.run()