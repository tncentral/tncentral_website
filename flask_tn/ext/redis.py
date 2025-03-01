
conn = None
# migrate = Migrate()

def init_app(connection):
    # database object creation
    global conn
    conn = connection
    # migrate.init_app(app, db)