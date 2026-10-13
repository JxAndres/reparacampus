from flask import Blueprint, g, render_template, request

from app.auth import obtener_db, rol_requerido
from app.prioridad import calcular_prioridad
from app.reloj import ahora

bp = Blueprint("asignaciones", __name__)

ORDEN_PRIORIDAD = {"CRITICA": 0, "ALTA": 1, "NORMAL": 2}


class ErrorNegocio(Exception):
    def __init__(self, estado_http, mensaje):
        super().__init__(mensaje)
        self.estado_http = estado_http
        self.mensaje = mensaje


def asignar_incidencia(conn, coordinador_id, incidencia_id, tecnico_id, momento):
    """Asigna un técnico en UNA transacción. Lanza ErrorNegocio si no procede."""
    incidencia = conn.execute(
        "SELECT id, estado FROM incidencias WHERE id = ?", (incidencia_id,)
    ).fetchone()
    if incidencia is None:
        raise ErrorNegocio(404, "La incidencia no existe.")
    if incidencia["estado"] != "REGISTRADA":
        raise ErrorNegocio(409, "Solo se puede asignar una incidencia REGISTRADA.")

    tecnico = conn.execute(
        "SELECT id, username FROM usuarios "
        "WHERE id = ? AND rol = 'TECNICO' AND activo = 1",
        (tecnico_id,),
    ).fetchone()
    if tecnico is None:
        raise ErrorNegocio(422, "El técnico no existe, está inactivo o no tiene rol TECNICO.")

    marca = momento.isoformat()
    with conn:  # si algo falla (incluida ErrorNegocio), se revierte todo
        cur = conn.execute(
            "UPDATE incidencias SET estado = 'ASIGNADA' "
            "WHERE id = ? AND estado = 'REGISTRADA'",
            (incidencia_id,),
        )
        if cur.rowcount == 0:
            raise ErrorNegocio(409, "La incidencia ya fue asignada.")
        conn.execute(
            "INSERT INTO asignaciones (incidencia_id, tecnico_id, coordinador_id, asignada_en) "
            "VALUES (?, ?, ?, ?)",
            (incidencia_id, tecnico["id"], coordinador_id, marca),
        )
        conn.execute(
            "INSERT INTO eventos (incidencia_id, accion, autor_id, estado_anterior, "
            "estado_nuevo, detalle, creado_en) "
            "VALUES (?, 'ASIGNAR', ?, 'REGISTRADA', 'ASIGNADA', ?, ?)",
            (incidencia_id, coordinador_id, f"Técnico: {tecnico['username']}", marca),
        )


def listar_pendientes(conn):
    filas = conn.execute(
        "SELECT i.id, i.codigo, i.ubicacion, i.categoria, i.descripcion, i.impacto, "
        "i.riesgo_personas, i.creada_en, u.nombre AS autor "
        "FROM incidencias i JOIN usuarios u ON u.id = i.autor_id "
        "WHERE i.estado = 'REGISTRADA' ORDER BY i.id"
    ).fetchall()
    pendientes = []
    for f in filas:
        d = dict(f)
        d["prioridad"] = calcular_prioridad(bool(f["riesgo_personas"]), f["impacto"])
        pendientes.append(d)
    pendientes.sort(key=lambda d: (ORDEN_PRIORIDAD[d["prioridad"]], d["id"]))
    return pendientes


def _pagina(conn, estado=200, errores=None, ok=None):
    tecnicos = conn.execute(
        "SELECT id, nombre FROM usuarios WHERE rol = 'TECNICO' AND activo = 1 ORDER BY id"
    ).fetchall()
    return render_template(
        "asignar.html",
        pendientes=listar_pendientes(conn),
        tecnicos=tecnicos,
        errores=errores or [],
        ok=ok,
    ), estado


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


@bp.route("/asignaciones")
@rol_requerido("COORDINADOR")
def pendientes():
    conn = obtener_db()
    try:
        return _pagina(conn)
    finally:
        conn.close()


@bp.route("/incidencias/<int:incidencia_id>/asignar", methods=["POST"])
@rol_requerido("COORDINADOR")
def asignar(incidencia_id):
    tecnico_id = _entero(request.form.get("tecnico_id"))  # la prioridad enviada se ignora
    conn = obtener_db()
    try:
        try:
            asignar_incidencia(conn, g.user["id"], incidencia_id, tecnico_id, ahora())
        except ErrorNegocio as e:
            return _pagina(conn, e.estado_http, errores=[e.mensaje])
        return _pagina(conn, ok="Incidencia asignada correctamente.")
    finally:
        conn.close()