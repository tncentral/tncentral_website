from flask_wtf import CSRFProtect

def init_app(app):
    CSRFProtect(app)