"""S05 · Consultar e historizar (RF05).

Listado con filtros por rol, detalle con historial y tablero del coordinador.
Todas las rutas son de solo lectura.
"""
from decimal import Decimal, ROUND_HALF_UP

from flask import Blueprint, abort, g, render_template, request

from app.auth import login_required, obtener_db, rol_requerido
from app.prioridad import calcular_prioridad

bp = Blueprint("consultas", __name__)

ESTADOS = ("REGISTRADA", "ASIGNADA", "EN_ATENCION", "PENDIENTE_VALIDACION", "CERRADA")
PRIORIDADES = ("CRITICA", "ALTA", "NORMAL")

BASE_SELECT = (
    "SELECT i.id, i.codigo, i.ubicacion, i.categoria, i.descripcion, i.impacto, "
    "i.riesgo_personas, i.estado, i.autor_id, a.tecnico_id "
    "FROM incidencias i LEFT JOIN asignaciones a ON a.incidencia_id = i.id "
)


def _con_prioridad(fila):
    """La prioridad no se guarda: se calcula."""
    d = dict(fila)
    d["prioridad"] = calcular_prioridad(bool(fila["riesgo_personas"]), fila["impacto"])
    return d


def _alcance(usuario):
    """Condición SQL y parámetros según el rol de la sesión."""
    if usuario["rol"] == "SOLICITANTE":
        return "WHERE i.autor_id = ? ", (usuario["id"],)
    if usuario["rol"] == "TECNICO":
        return "WHERE a.tecnico_id = ? ", (usuario["id"],)
    return "", ()          # el coordinador ve todas


def _puede_ver(usuario, fila):
    if usuario["rol"] == "COORDINADOR":
        return True
    if usuario["rol"] == "SOLICITANTE":
        return fila["autor_id"] == usuario["id"]
    if usuario["rol"] == "TECNICO":
        return fila["tecnico_id"] == usuario["id"]
    return False


def listar(conn, usuario, estado="", prioridad=""):
    """Primero el alcance por rol y luego los filtros."""
    donde, params = _alcance(usuario)
    consulta = BASE_SELECT + donde
    if estado:
        consulta += ("AND " if donde else "WHERE ") + "i.estado = ? "
        params = params + (estado,)
    consulta += "ORDER BY i.id"
    filas = [_con_prioridad(f) for f in conn.execute(consulta, params).fetchall()]
    if prioridad:
        filas = [f for f in filas if f["prioridad"] == prioridad]
    return filas


def porcentaje_cierre(cerradas, total):
    """CERRADAS / total x 100, un decimal, coma decimal, mitad hacia arriba."""
    if total == 0:
        return "0,0 %"
    valor = (Decimal(cerradas) * 100 / Decimal(total)).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{valor}".replace(".", ",") + " %"


def calcular_tablero(conn):
    filas = [_con_prioridad(f) for f in conn.execute(
        "SELECT estado, riesgo_personas, impacto FROM incidencias").fetchall()]
    total = len(filas)
    cerradas = sum(1 for f in filas if f["estado"] == "CERRADA")
    return {
        "total": total,
        "por_estado": [(e, sum(1 for f in filas if f["estado"] == e)) for e in ESTADOS],
        "por_prioridad": [(p, sum(1 for f in filas if f["prioridad"] == p))
                          for p in PRIORIDADES],
        "criticas_abiertas": sum(1 for f in filas if f["prioridad"] == "CRITICA"
                                 and f["estado"] != "CERRADA"),
        "porcentaje": porcentaje_cierre(cerradas, total),
    }


def _pagina_lista(incidencias, errores, estado, prioridad, codigo=200):
    return render_template("lista.html", incidencias=incidencias, errores=errores,
                           estado=estado, prioridad=prioridad,
                           estados=ESTADOS, prioridades=PRIORIDADES), codigo


@bp.route("/incidencias")
@login_required
def listado():
    estado = (request.args.get("estado") or "").strip()
    prioridad = (request.args.get("prioridad") or "").strip()
    errores = []
    if estado and estado not in ESTADOS:
        errores.append("El estado indicado no es válido.")
    if prioridad and prioridad not in PRIORIDADES:
        errores.append("La prioridad indicada no es válida.")
    if errores:
        return _pagina_lista([], errores, estado, prioridad, 400)
    conn = obtener_db()
    try:
        filas = listar(conn, g.user, estado, prioridad)
    finally:
        conn.close()
    return _pagina_lista(filas, [], estado, prioridad)


@bp.route("/incidencias/<int:incidencia_id>")
@login_required
def detalle(incidencia_id):
    conn = obtener_db()
    try:
        fila = conn.execute(BASE_SELECT + "WHERE i.id = ?", (incidencia_id,)).fetchone()
        if fila is None:
            abort(404)                      # inexistente
        if not _puede_ver(g.user, fila):
            abort(403)                      # existe pero no es suya
        historial = conn.execute(
            "SELECT e.id, e.accion, e.estado_anterior, e.estado_nuevo, e.detalle, "
            "e.creado_en, u.nombre AS autor FROM eventos e "
            "JOIN usuarios u ON u.id = e.autor_id WHERE e.incidencia_id = ? "
            "ORDER BY e.creado_en ASC, e.id ASC", (incidencia_id,)).fetchall()
        soluciones = conn.execute(
            "SELECT s.texto, s.registrada_en, u.nombre AS tecnico FROM soluciones s "
            "JOIN usuarios u ON u.id = s.tecnico_id WHERE s.incidencia_id = ? "
            "ORDER BY s.id", (incidencia_id,)).fetchall()
    finally:
        conn.close()
    return render_template("detalle.html", i=_con_prioridad(fila),
                           historial=historial, soluciones=soluciones)


@bp.route("/tablero")
@rol_requerido("COORDINADOR")
def tablero():
    conn = obtener_db()
    try:
        datos = calcular_tablero(conn)
    finally:
        conn.close()
    return render_template("tablero.html", **datos)