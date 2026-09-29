from flask import Flask

from app.config import Config
from app.extensions import db, migrate, login_manager, bcrypt, mail


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    login_manager.login_view = "auth.login"
    # Shown as a flash message if someone hits a @login_required route
    # without being logged in, before they're bounced to the login page.
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "info"

    # Import models so they register with SQLAlchemy before any
    # migration or query touches the database.
    from app import models  # noqa: F401

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.route("/health")
    def health_check():
        return {"status": "ok"}

    return app
