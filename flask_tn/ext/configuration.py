import os
from dynaconf import FlaskDynaconf

def init_app(app):
    FlaskDynaconf(app)

def update_config(app):
    if app.config['ENV']=="development":
        home = app.config['TNC_HOME']
    else:
        home = app.config["TNC_HOME_PRODUCTION"]

    app.config['TNC_DATA_DIR'] = os.path.join(home, app.config['TNC_DATA_DIR'])
    app.config['TNC_BASE_DIR'] = os.path.join(app.config['TNC_DATA_DIR'], app.config['TNC_BASE_DIR'])
    app.config['TNC_CURRENT_DIR'] = os.path.join(app.config['TNC_DATA_DIR'], app.config['TNC_CURRENT_DIR'])

    app.config["QC_SCRIPT"] = os.path.join(home, app.config["QC_SCRIPT"])
    app.config["QC_ACCESSORY"] = os.path.join(app.config['TNC_DATA_DIR'], app.config["QC_ACCESSORY"])

    app.config['SQLALCHEMY_DATABASE_LOCATION'] = os.path.join(app.config['TNC_CURRENT_DIR'],app.config['TNC_DATABASE_NAME'])
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+app.config['SQLALCHEMY_DATABASE_LOCATION']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
