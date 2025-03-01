# # ============= #
# # CONFIGURATION #
# # ============= #
from flask import Flask
from flask_wtf import CSRFProtect
from .ext import configuration, database, mail, login, csrf, logging
from .blueprints import webui, restapi, admin

def create_app():
	"""
		This function builds the flask object application.
	"""
	app = Flask(__name__)
	app.secret_key = 'coconut_transposons'
	app.jinja_env.globals.update(configure_active=webui.configure_active)
	app.jinja_env.globals.update(check_image=webui.check_image)
	app.jinja_env.globals.update(check_file=webui.check_file)
	app.jinja_env.globals.update(use_analytics=webui.use_analytics)
	app.jinja_env.globals.update(use_recaptcha=webui.use_recaptcha)
	app.jinja_env.globals.update(configure_active2=admin.configure_active2)

	# external modules
	configuration.init_app(app)
	configuration.update_config(app)
	database.init_app(app)
	# flask_login module
	login.init_app(app)
	# Cross-Site Request Forgery(CSRF) protection
	csrf.init_app(app)

	# blueprints
	webui.init_app(app)
	restapi.init_app(app)
	admin.init_app(app)
	# flask_rq.init_app(app)
	# mail.init_app(app)
	logging.init_app(app)
	return app

