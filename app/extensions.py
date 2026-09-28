from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
# Flask-Mail wraps Python's built-in smtplib so the rest of the app can just
# call mail.send(message) instead of hand-rolling an SMTP connection every
# time we need to email someone (right now: password reset).
mail = Mail()
