import os

from flask import Flask

from app import atencion, auth, incidencias


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "clave-solo-para-desarrollo")
    app.config["DB_PATH"] = db_path
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.register_blueprint(auth.bp)
    app.register_blueprint(incidencias.bp)
    app.register_blueprint(atencion.bp)
    return app