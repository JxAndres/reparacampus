from flask import Blueprint, g, render_template, request

from app.auth import obtener_db, rol_requerido
from app.reloj import ahora

bp = Blueprint("incidencias", __name__)

UBICACIONES = ("LAB-01", "AULA-201", "BIB-01")
CATEGORIAS = ("ELECTRICIDAD", "HIDRAULICA", "MOBILIARIO", "TIC")
IMPACTOS = ("BAJO", "ALTO")


def validar_incidencia(datos):
    """Valida los datos del formulario. Devuelve (datos_limpios, errores)."""
    ubicacion = (datos.get("ubicacion") or "").strip()
    categoria = (datos.get("categoria") or "").strip()
    descripcion = (datos.get("descripcion") or "").strip()
    impacto = (datos.get("impacto") or "").strip()
    riesgo = (datos.get("riesgo_personas") or "").strip()

    errores = []
    if ubicacion not in UBICACIONES:
        errores.append("Ubicación no válida.")
    if categoria not in CATEGORIAS:
        errores.append("Categoría no válida.")
    if not 20 <= len(descripcion) <= 500:
        errores.append("La descripción debe tener entre 20 y 500 caracteres.")
    if impacto not in IMPACTOS:
        errores.append("El impacto debe ser BAJO o ALTO.")
    if riesgo not in ("true", "false"):
        errores.append("El riesgo para personas debe ser true o false.")

    limpio = {
        "ubicacion": ubicacion,
        "categoria": categoria,
        "descripcion": descripcion,
        "impacto": impacto,
        "riesgo_personas": 1 if riesgo == "true" else 0,
    }
    return limpio, errores


def crear_incidencia(conn, autor_id, datos, momento):
    """Crea la incidencia y su evento en UNA sola transacción."""
    marca = momento.isoformat()
    with conn:  # confirma si todo sale bien; revierte todo si algo falla
        cur = conn.execute(
            "INSERT INTO incidencias (ubicacion, categoria, descripcion, impacto, "
            "riesgo_personas, estado, autor_id, creada_en) "
            "VALUES (?, ?, ?, ?, ?, 'REGISTRADA', ?, ?)",
            (datos["ubicacion"], datos["categoria"], datos["descripcion"],
             datos["impacto"], datos["riesgo_personas"], autor_id, marca),
        )
        incidencia_id = cur.lastrowid
        codigo = f"INC-{incidencia_id:04d}"
        conn.execute("UPDATE incidencias SET codigo = ? WHERE id = ?",
                     (codigo, incidencia_id))
        conn.execute(
            "INSERT INTO eventos (incidencia_id, accion, autor_id, estado_anterior, "
            "estado_nuevo, detalle, creado_en) "
            "VALUES (?, 'CREAR', ?, NULL, 'REGISTRADA', NULL, ?)",
            (incidencia_id, autor_id, marca),
        )
    return codigo


def _contexto(**extra):
    base = {"ubicaciones": UBICACIONES, "categorias": CATEGORIAS,
            "valores": {}, "errores": [], "creada": None}
    base.update(extra)
    return base


@bp.route("/incidencias/nueva")
@rol_requerido("SOLICITANTE")
def nueva():
    return render_template("nueva.html", **_contexto())


@bp.route("/incidencias", methods=["POST"])
@rol_requerido("SOLICITANTE")
def crear():
    limpio, errores = validar_incidencia(request.form)
    if errores:
        return render_template(
            "nueva.html", **_contexto(valores=request.form, errores=errores)), 400
    conn = obtener_db()
    try:
        codigo = crear_incidencia(conn, g.user["id"], limpio, ahora())
    finally:
        conn.close()
    return render_template("nueva.html", **_contexto(creada=codigo)), 201