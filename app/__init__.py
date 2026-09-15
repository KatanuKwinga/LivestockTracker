from flask import Flask

from app.config import Config
from app.extensions import db, migrate, login_manager, bcrypt


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    login_manager.login_view = "auth.login"

    # Import models so they register with SQLAlchemy before any
    # migration or query touches the database.
    from app import models  # noqa: F401

    # Blueprints are registered here as each is built in later steps.
    # from app.routes.auth import auth_bp
    # app.register_blueprint(auth_bp)

    @app.route("/health")
    def health_check():
        return {"status": "ok"}

    return app
