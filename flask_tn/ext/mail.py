# from flask_mail import Mail

# mail_obj = Mail()

# def init_app(app):
#     global mail_obj
#     mail_obj.init_app(app)

from flask import Flask, request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart