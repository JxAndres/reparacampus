import functools

from flask import (
    Blueprint, abort, current_app, flash, g, redirect,
    render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash

from app.db import get_connection

bp = Blueprint("auth", __name__)


def obtener_db():
    return get_connection(current_app.config.get("DB_PATH"))


@bp.before_app_request
def cargar_usuario():
    """Identidad y rol salen siempre de la sesión del servidor."""
    g.user = None
    user_id = session.get("user_id")
    if user_id is None:
        return
    conn = obtener_db()
    fila = conn.execute(
        "SELECT id, username, nombre, rol, activo FROM usuarios WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if fila is None or not fila["activo"]:
        session.clear()
        return
    g.user = fila


def login_required(vista):
    @functools.wraps(vista)
    def envoltura(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)
    return envoltura


def rol_requerido(*roles):
    """Sin sesión: redirige al login. Con rol incorrecto: 403."""
    def decorador(vista):
        @functools.wraps(vista)
        def envoltura(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("auth.login"))
            if g.user["rol"] not in roles:
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = obtener_db()
        fila = conn.execute(
            "SELECT id, password_hash, activo FROM usuarios WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()
        if fila and fila["activo"] and check_password_hash(fila["password_hash"], password):
            session.clear()
            session["user_id"] = fila["id"]
            return redirect(url_for("auth.index"))
        flash("Usuario o contraseña incorrectos.")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/")
@login_required
def index():
    return render_template("index.html")