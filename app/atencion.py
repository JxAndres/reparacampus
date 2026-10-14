"""S03 · Atender incidencia (RF03).

Iniciar atención:   ASIGNADA     -> EN_ATENCION
Registrar solución: EN_ATENCION  -> PENDIENTE_VALIDACION
"""
from flask import Blueprint, g, render_template, request

from app import reloj
from app.auth import obtener_db, rol_requerido

bp = Blueprint("atencion", __name__)

SOLUCION_MIN = 20
SOLUCION_MAX = 800

# Nombres de acción del historial. Deben estar permitidos por el CHECK de
# schema.sql. PENDIENTE: confirmar con Juan (las SPECS dicen INICIAR_ATENCION
# y REGISTRAR_SOLUCION).
ACCION_INICIAR = "INICIAR"
ACCION_SOLUCION = "PROPONER_SOLUCION"


class ErrorAtencion(Exception):
    """Error de negocio con el código HTTP que debe devolverse."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _verificar_tecnico(conn, incidencia_id, tecnico_id):
    """Devuelve el estado actual o lanza 404 / 409 / 403."""
    fila = conn.execute(
        "SELECT i.estado, a.tecnico_id FROM incidencias i "
        "LEFT JOIN asignaciones a ON a.incidencia_id = i.id "
        "WHERE i.id = ?",
        (incidencia_id,),
    ).fetchone()
    if fila is None:
        raise ErrorAtencion(404, "La incidencia no existe.")
    if fila["tecnico_id"] is None:
        raise ErrorAtencion(409, "La incidencia aún no tiene técnico asignado.")
    if fila["tecnico_id"] != tecnico_id:
        raise ErrorAtencion(403, "Solo el técnico asignado puede operar.")
    return fila["estado"]


def _cambiar_estado(conn, incidencia_id, desde, hacia):
    """Cambia el estado solo si sigue siendo `desde` (evita operaciones dobles)."""
    cur = conn.execute(
        "UPDATE incidencias SET estado = ? WHERE id = ? AND estado = ?",
        (hacia, incidencia_id, desde),
    )
    if cur.rowcount != 1:
        raise ErrorAtencion(409, f"La incidencia ya no está {desde}.")


def _insertar_evento(conn, incidencia_id, accion, autor_id,
                     anterior, nuevo, detalle, momento):
    conn.execute(
        "INSERT INTO eventos (incidencia_id, accion, autor_id, estado_anterior, "
        "estado_nuevo, detalle, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (incidencia_id, accion, autor_id, anterior, nuevo, detalle,
         momento.isoformat()),
    )


def iniciar_atencion(conn, incidencia_id, tecnico_id, momento):
    """ASIGNADA -> EN_ATENCION, con su evento, en UNA sola transacción."""
    with conn:
        estado = _verificar_tecnico(conn, incidencia_id, tecnico_id)
        if estado != "ASIGNADA":
            raise ErrorAtencion(409, "Solo se puede iniciar una incidencia ASIGNADA.")
        _cambiar_estado(conn, incidencia_id, "ASIGNADA", "EN_ATENCION")
        _insertar_evento(conn, incidencia_id, ACCION_INICIAR, tecnico_id,
                         "ASIGNADA", "EN_ATENCION", None, momento)
    return "EN_ATENCION"


def registrar_solucion(conn, incidencia_id, tecnico_id, texto, momento):
    """EN_ATENCION -> PENDIENTE_VALIDACION, con solución y evento, en UNA transacción."""
    with conn:
        estado = _verificar_tecnico(conn, incidencia_id, tecnico_id)
        if estado != "EN_ATENCION":
            raise ErrorAtencion(409, "Solo se puede registrar solución en EN_ATENCION.")
        solucion = (texto or "").strip()
        if not SOLUCION_MIN <= len(solucion) <= SOLUCION_MAX:
            raise ErrorAtencion(
                400, "La solución debe tener entre 20 y 800 caracteres.")
        _cambiar_estado(conn, incidencia_id, "EN_ATENCION", "PENDIENTE_VALIDACION")
        conn.execute(
            "INSERT INTO soluciones (incidencia_id, tecnico_id, texto, registrada_en) "
            "VALUES (?, ?, ?, ?)",
            (incidencia_id, tecnico_id, solucion, momento.isoformat()),
        )
        _insertar_evento(conn, incidencia_id, ACCION_SOLUCION, tecnico_id,
                         "EN_ATENCION", "PENDIENTE_VALIDACION", solucion, momento)
    return "PENDIENTE_VALIDACION"


def listar_asignadas(conn, tecnico_id):
    """Solo las incidencias asignadas al técnico de la sesión."""
    return conn.execute(
        "SELECT i.id, i.codigo, i.ubicacion, i.categoria, i.descripcion, i.estado "
        "FROM incidencias i JOIN asignaciones a ON a.incidencia_id = i.id "
        "WHERE a.tecnico_id = ? ORDER BY i.id",
        (tecnico_id,),
    ).fetchall()


def _pagina(conn, estado=200, errores=None, ok=None):
    return render_template(
        "atencion.html",
        asignadas=listar_asignadas(conn, g.user["id"]),
        errores=errores or [],
        ok=ok,
    ), estado


@bp.route("/atencion")
@rol_requerido("TECNICO")
def mis_asignaciones():
    conn = obtener_db()
    try:
        return _pagina(conn)
    finally:
        conn.close()


@bp.route("/incidencias/<int:incidencia_id>/iniciar", methods=["POST"])
@rol_requerido("TECNICO")
def iniciar(incidencia_id):
    conn = obtener_db()
    try:
        try:
            iniciar_atencion(conn, incidencia_id, g.user["id"], reloj.ahora())
        except ErrorAtencion as e:
            return _pagina(conn, e.codigo, errores=[e.mensaje])
        return _pagina(conn, ok="Atención iniciada correctamente.")
    finally:
        conn.close()


@bp.route("/incidencias/<int:incidencia_id>/solucion", methods=["POST"])
@rol_requerido("TECNICO")
def solucion(incidencia_id):
    conn = obtener_db()
    try:
        try:
            registrar_solucion(conn, incidencia_id, g.user["id"],
                               request.form.get("solucion"), reloj.ahora())
        except ErrorAtencion as e:
            return _pagina(conn, e.codigo, errores=[e.mensaje])
        return _pagina(conn, ok="Solución registrada correctamente.")
    finally:
        conn.close()