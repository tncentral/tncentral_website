from flask_rq2 import RQ

rq = RQ()

def init_app(app):
    rq.init_app(app)
