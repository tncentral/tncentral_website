import os
import logging
from logging.handlers import RotatingFileHandler

def init_app(app):
    if app.config['ENV']=="development":
        home = app.config['TNC_HOME']
    else:
        home = app.config["TNC_HOME_PRODUCTION"]
    # database object creation
    log_dir = os.path.join(home, app.config["TNC_LOG_DIR"])

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    app_log = os.path.join(log_dir, app.config["TNC_LOG_FILE"])

    app.logger.setLevel(logging.INFO)  # Set log level to INFO
    handler = RotatingFileHandler(app_log, maxBytes=2097152)  # Log to a file
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    app.logger.addHandler(handler)
