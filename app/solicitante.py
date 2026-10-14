"""Pantalla del solicitante para validar soluciones (interfaz de S04, RF04).

Las reglas viven en app/validacion.py (confirmar, rechazar, reabrir). Este módulo solo
muestra las incidencias PROPIAS del solicitante y llama a esas funciones.
"""
from flask import Blueprint, g, render_template, request

from app import reloj, validacion
from app.auth import obtener_db, rol_requerido
from app.validacion import ErrorValidacion

bp = Blueprint("solicitante", __name__)


def listar_propias(conn, usuario_id):
    """Solo las incidencias registradas por el solicitante de la sesión."""
    filas = conn.execute(
        "SELECT id, codigo, ubicacion, categoria, descripcion, estado "
        "FROM incidencias WHERE autor_id = ? ORDER BY id",
        (usuario_id,),
    ).fetchall()
    propias = []
    for fila in filas:
        incidencia = dict(fila)
        ultima = conn.execute(
            "SELECT texto FROM soluciones WHERE incidencia_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (fila["id"],),
        ).fetchone()
        incidencia["solucion"] = ultima["texto"] if ultima else None
        propias.append(incidencia)
    return propias


def _pagina(conn, estado=200, errores=None, ok=None):
    return render_template(
        "solicitante.html",
        propias=listar_propias(conn, g.user["id"]),
        errores=errores or [],
        ok=ok,
    ), estado


def _operar(operacion, mensaje_ok):
    conn = obtener_db()
    try:
        try:
            operacion(conn)
        except ErrorValidacion as e:
            return _pagina(conn, e.codigo, errores=[e.mensaje])
        return _pagina(conn, ok=mensaje_ok)
    finally:
        conn.close()


@bp.route("/mis-incidencias")
@rol_requerido("SOLICITANTE")
def mis_incidencias():
    conn = obtener_db()
    try:
        return _pagina(conn)
    finally:
        conn.close()


@bp.route("/mis-incidencias/<int:incidencia_id>/confirmar", methods=["POST"])
@rol_requerido("SOLICITANTE")
def confirmar(incidencia_id):
    return _operar(
        lambda conn: validacion.confirmar(
            conn, incidencia_id, g.user["id"], reloj.ahora()),
        "Solución confirmada. La incidencia quedó cerrada.")


@bp.route("/mis-incidencias/<int:incidencia_id>/rechazar", methods=["POST"])
@rol_requerido("SOLICITANTE")
def rechazar(incidencia_id):
    return _operar(
        lambda conn: validacion.rechazar(
            conn, incidencia_id, g.user["id"],
            request.form.get("motivo"), reloj.ahora()),
        "Solución rechazada. La incidencia volvió a atención con el mismo técnico.")


@bp.route("/mis-incidencias/<int:incidencia_id>/reabrir", methods=["POST"])
@rol_requerido("SOLICITANTE")
def reabrir(incidencia_id):
    return _operar(
        lambda conn: validacion.reabrir(
            conn, incidencia_id, g.user["id"],
            request.form.get("motivo"), reloj.ahora()),
        "Incidencia reabierta. Volvió a atención con el mismo técnico.")