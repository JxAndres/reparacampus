"""S04 · Validar solución (RF04).

Confirmar: PENDIENTE_VALIDACION -> CERRADA
Rechazar:  PENDIENTE_VALIDACION -> EN_ATENCION (con motivo)
Reabrir:   CERRADA -> EN_ATENCION (con motivo, hasta 48 h después del último cierre)
"""
from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify, request

from app import reloj
from app.auth import obtener_db, rol_requerido

bp = Blueprint("validacion", __name__)

MOTIVO_MIN = 10
MOTIVO_MAX = 300
PLAZO_REAPERTURA = timedelta(hours=48)

# Nombres de acción del historial: son los que acepta el CHECK de schema.sql.
ACCION_CONFIRMAR = "CONFIRMAR"
ACCION_RECHAZAR = "RECHAZAR"
ACCION_REABRIR = "REABRIR"


class ErrorValidacion(Exception):
    """Error de negocio con el código HTTP que debe devolverse."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _verificar_dueno(conn, incidencia_id, usuario_id):
    """Devuelve el estado actual o lanza 404 / 403."""
    fila = conn.execute(
        "SELECT estado, autor_id FROM incidencias WHERE id = ?",
        (incidencia_id,),
    ).fetchone()
    if fila is None:
        raise ErrorValidacion(404, "La incidencia no existe.")
    if fila["autor_id"] != usuario_id:
        raise ErrorValidacion(403, "Solo el solicitante dueño puede operar.")
    return fila["estado"]


def _exigir_estado(estado, esperado):
    if estado != esperado:
        raise ErrorValidacion(409, f"La incidencia debe estar {esperado}.")


def _validar_motivo(texto):
    motivo = (texto or "").strip()
    if not MOTIVO_MIN <= len(motivo) <= MOTIVO_MAX:
        raise ErrorValidacion(
            400, "El motivo debe tener entre 10 y 300 caracteres.")
    return motivo


def _cambiar_estado(conn, incidencia_id, desde, hacia):
    """Cambia el estado solo si sigue siendo `desde` (evita operaciones dobles)."""
    cur = conn.execute(
        "UPDATE incidencias SET estado = ? WHERE id = ? AND estado = ?",
        (hacia, incidencia_id, desde),
    )
    if cur.rowcount != 1:
        raise ErrorValidacion(409, f"La incidencia ya no está {desde}.")


def _insertar_evento(conn, incidencia_id, accion, autor_id,
                     anterior, nuevo, detalle, momento):
    conn.execute(
        "INSERT INTO eventos (incidencia_id, accion, autor_id, estado_anterior, "
        "estado_nuevo, detalle, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (incidencia_id, accion, autor_id, anterior, nuevo, detalle,
         momento.isoformat()),
    )


def _ultimo_cierre(conn, incidencia_id):
    """Fecha UTC del último cierre = último evento CONFIRMAR de la incidencia."""
    fila = conn.execute(
        "SELECT creado_en FROM eventos WHERE incidencia_id = ? AND accion = ? "
        "ORDER BY id DESC LIMIT 1",
        (incidencia_id, ACCION_CONFIRMAR),
    ).fetchone()
    if fila is None:
        raise ErrorValidacion(409, "La incidencia no tiene un cierre registrado.")
    return datetime.fromisoformat(fila["creado_en"])


def confirmar(conn, incidencia_id, usuario_id, momento):
    """PENDIENTE_VALIDACION -> CERRADA, con su evento, en UNA transacción."""
    with conn:
        estado = _verificar_dueno(conn, incidencia_id, usuario_id)
        _exigir_estado(estado, "PENDIENTE_VALIDACION")
        _cambiar_estado(conn, incidencia_id, "PENDIENTE_VALIDACION", "CERRADA")
        _insertar_evento(conn, incidencia_id, ACCION_CONFIRMAR, usuario_id,
                         "PENDIENTE_VALIDACION", "CERRADA", None, momento)
    return "CERRADA"


def rechazar(conn, incidencia_id, usuario_id, texto_motivo, momento):
    """PENDIENTE_VALIDACION -> EN_ATENCION. Conserva técnico y solución."""
    with conn:
        estado = _verificar_dueno(conn, incidencia_id, usuario_id)
        _exigir_estado(estado, "PENDIENTE_VALIDACION")
        motivo = _validar_motivo(texto_motivo)
        _cambiar_estado(conn, incidencia_id, "PENDIENTE_VALIDACION", "EN_ATENCION")
        _insertar_evento(conn, incidencia_id, ACCION_RECHAZAR, usuario_id,
                         "PENDIENTE_VALIDACION", "EN_ATENCION", motivo, momento)
    return "EN_ATENCION"


def reabrir(conn, incidencia_id, usuario_id, texto_motivo, momento):
    """CERRADA -> EN_ATENCION si pasaron 48 h o menos desde el último cierre."""
    with conn:
        estado = _verificar_dueno(conn, incidencia_id, usuario_id)
        _exigir_estado(estado, "CERRADA")
        motivo = _validar_motivo(texto_motivo)
        cierre = _ultimo_cierre(conn, incidencia_id)
        if momento - cierre > PLAZO_REAPERTURA:
            raise ErrorValidacion(409, "Pasaron más de 48 horas desde el cierre.")
        _cambiar_estado(conn, incidencia_id, "CERRADA", "EN_ATENCION")
        _insertar_evento(conn, incidencia_id, ACCION_REABRIR, usuario_id,
                         "CERRADA", "EN_ATENCION", motivo, momento)
    return "EN_ATENCION"


def _ejecutar(operacion):
    conn = obtener_db()
    try:
        estado = operacion(conn)
    except ErrorValidacion as e:
        return jsonify(error=e.mensaje), e.codigo
    finally:
        conn.close()
    return jsonify(estado=estado)


@bp.route("/incidencias/<int:incidencia_id>/confirmar", methods=["POST"])
@rol_requerido("SOLICITANTE")
def ruta_confirmar(incidencia_id):
    return _ejecutar(lambda conn: confirmar(
        conn, incidencia_id, g.user["id"], reloj.ahora()))


@bp.route("/incidencias/<int:incidencia_id>/rechazar", methods=["POST"])
@rol_requerido("SOLICITANTE")
def ruta_rechazar(incidencia_id):
    return _ejecutar(lambda conn: rechazar(
        conn, incidencia_id, g.user["id"],
        request.form.get("motivo"), reloj.ahora()))


@bp.route("/incidencias/<int:incidencia_id>/reabrir", methods=["POST"])
@rol_requerido("SOLICITANTE")
def ruta_reabrir(incidencia_id):
    return _ejecutar(lambda conn: reabrir(
        conn, incidencia_id, g.user["id"],
        request.form.get("motivo"), reloj.ahora()))