import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def init_app(app):
    # database object creation
    db.init_app(app)
    migrate.init_app(app, db)