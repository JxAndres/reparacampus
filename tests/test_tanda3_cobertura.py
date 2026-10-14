"""Tanda 3: cierra los criterios de S01 a S05 que quedaban sin prueba automatizada.

Valores ESPERADOS escritos a mano antes de ejecutar. Reloj controlado.
Las pruebas de atomicidad instalan un trigger que hace fallar el INSERT en `eventos`
y llaman a las funciones de negocio directamente (fallo simulado, AC de atomicidad).
"""
import re
import sqlite3
from datetime import timedelta

import pytest

from app import create_app
from app.asignaciones import asignar_incidencia
from app.atencion import iniciar_atencion, registrar_solucion
from app.validacion import confirmar, rechazar, reabrir
from tests.conftest import CLAVES

S1 = "Se reemplazo el cable danado y se probo la toma"
S2 = "Se cambio la regleta completa y se midio el voltaje"
MOTIVO = "Motivo valido de prueba"
SCRIPT = "<script>alert(1)</script>"
ORDEN = ["REGISTRADA", "ASIGNADA", "EN_ATENCION", "PENDIENTE_VALIDACION", "CERRADA"]


def contar(db, tabla):
    return db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


def estado(db, i):
    return db.execute("SELECT estado FROM incidencias WHERE id=?", (i,)).fetchone()[0]


def acciones(db, i):
    return [f[0] for f in db.execute("SELECT accion FROM eventos WHERE incidencia_id=? ORDER BY id", (i,))]


def codigo(i):
    return f"INC-{i:04d}"


def conexion_que_falla_al_guardar_evento(ruta_db):
    conn = sqlite3.connect(ruta_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("CREATE TRIGGER falla_evento BEFORE INSERT ON eventos "
                 "BEGIN SELECT RAISE(ABORT, 'fallo simulado'); END;")
    conn.commit()
    return conn


@pytest.fixture
def ciclo(registrar, cliente_de, id_de, db):
    class Ciclo:
        def __init__(self):
            self._c = {}

        def c(self, usuario):
            if usuario not in self._c:
                self._c[usuario] = cliente_de(usuario)
            return self._c[usuario]

        def post(self, usuario, ruta, **datos):
            return self.c(usuario).post(ruta, data=datos).status_code

        def nueva(self, usuario="solicitante1", **datos):
            assert registrar(usuario, **datos).status_code == 201
            return db.execute("SELECT MAX(id) FROM incidencias").fetchone()[0]

        def en_estado(self, objetivo, **datos):
            i = self.nueva(**datos)
            pasos = [
                lambda: self.post("coordinador1", f"/incidencias/{i}/asignar", tecnico_id=id_de("tecnico1")),
                lambda: self.post("tecnico1", f"/incidencias/{i}/iniciar"),
                lambda: self.post("tecnico1", f"/incidencias/{i}/solucion", solucion=S1),
                lambda: self.post("solicitante1", f"/incidencias/{i}/confirmar"),
            ]
            for paso in pasos[:ORDEN.index(objetivo)]:
                assert paso() == 200
            assert estado(db, i) == objetivo
            return i

        def solucion(self, i, texto, usuario="tecnico1"):
            return self.post(usuario, f"/incidencias/{i}/solucion", solucion=texto)

        def rechazar(self, i, motivo=MOTIVO, usuario="solicitante1", **extra):
            return self.post(usuario, f"/incidencias/{i}/rechazar", motivo=motivo, **extra)

        def reabrir(self, i, motivo=MOTIVO, usuario="solicitante1", **extra):
            return self.post(usuario, f"/incidencias/{i}/reabrir", motivo=motivo, **extra)
    return Ciclo()


# ------------------------------------------------------------------ S01 / S02
def test_pt22_descripcion_500_se_acepta_y_501_se_rechaza(ciclo, registrar, db):
    """PT-22 · AC-S01-05. Esperado: 501 → 400 sin guardar; 500 → 201."""
    assert registrar(descripcion="x" * 501).status_code == 400
    assert contar(db, "incidencias") == 0
    assert registrar(descripcion="x" * 500).status_code == 201
    assert contar(db, "incidencias") == 1


def test_pt23_asignacion_tecnico_inactivo_estados_y_prioridad_ignorada(ciclo, db, ruta_db, id_de):
    """PT-23 · AC-S02-07, 08, 09. Esperado: técnico inactivo → 422; asignar en EN_ATENCION o
    CERRADA → 409 sin cambios; un campo `prioridad` del cliente se ignora (queda NORMAL)."""
    i = ciclo.nueva()                                   # BAJO, sin riesgo → NORMAL
    en_atencion = ciclo.en_estado("EN_ATENCION")
    cerrada = ciclo.en_estado("CERRADA")
    conn = sqlite3.connect(ruta_db)
    conn.execute("UPDATE usuarios SET activo=0 WHERE username='tecnico2'")
    conn.commit()
    conn.close()

    ruta = f"/incidencias/{i}/asignar"
    assert ciclo.post("coordinador1", ruta, tecnico_id=id_de("tecnico2")) == 422
    assert estado(db, i) == "REGISTRADA" and contar(db, "asignaciones") == 2

    for otra, est in ((en_atencion, "EN_ATENCION"), (cerrada, "CERRADA")):
        antes = acciones(db, otra)
        assert ciclo.post("coordinador1", f"/incidencias/{otra}/asignar", tecnico_id=id_de("tecnico1")) == 409
        assert estado(db, otra) == est and acciones(db, otra) == antes

    assert ciclo.post("coordinador1", ruta, tecnico_id=id_de("tecnico1"), prioridad="CRITICA") == 200
    coord = ciclo.c("coordinador1")
    assert codigo(i) in coord.get("/incidencias?prioridad=NORMAL").get_data(as_text=True)
    assert codigo(i) not in coord.get("/incidencias?prioridad=CRITICA").get_data(as_text=True)


# ------------------------------------------------------------- atomicidad
def test_pt24_atomicidad_asignar_iniciar_y_registrar_solucion(ciclo, db, ruta_db, id_de, reloj):
    """PT-24 · AC-S02-10, AC-S03-16. Con fallo simulado al guardar el evento:
    nada queda a medias (ni asignación, ni cambio de estado, ni solución)."""
    registrada = ciclo.en_estado("REGISTRADA")
    asignada = ciclo.en_estado("ASIGNADA")
    en_atencion = ciclo.en_estado("EN_ATENCION")
    soluciones_antes = contar(db, "soluciones")
    conn = conexion_que_falla_al_guardar_evento(ruta_db)

    with pytest.raises(sqlite3.DatabaseError):
        asignar_incidencia(conn, id_de("coordinador1"), registrada, id_de("tecnico1"), reloj())
    assert estado(db, registrada) == "REGISTRADA"
    assert db.execute("SELECT COUNT(*) FROM asignaciones WHERE incidencia_id=?", (registrada,)).fetchone()[0] == 0

    with pytest.raises(sqlite3.DatabaseError):
        iniciar_atencion(conn, asignada, id_de("tecnico1"), reloj())
    assert estado(db, asignada) == "ASIGNADA"

    with pytest.raises(sqlite3.DatabaseError):
        registrar_solucion(conn, en_atencion, id_de("tecnico1"), S1, reloj())
    assert estado(db, en_atencion) == "EN_ATENCION"
    assert contar(db, "soluciones") == soluciones_antes
    conn.close()


def test_pt25_atomicidad_confirmar_rechazar_y_reabrir(ciclo, db, ruta_db, id_de, reloj):
    """PT-25 · AC-S04-18. Con fallo simulado al guardar el evento, el estado no cambia."""
    p1 = ciclo.en_estado("PENDIENTE_VALIDACION")
    p2 = ciclo.en_estado("PENDIENTE_VALIDACION")
    c = ciclo.en_estado("CERRADA")
    dueno = id_de("solicitante1")
    conn = conexion_que_falla_al_guardar_evento(ruta_db)

    with pytest.raises(sqlite3.DatabaseError):
        confirmar(conn, p1, dueno, reloj())
    with pytest.raises(sqlite3.DatabaseError):
        rechazar(conn, p2, dueno, MOTIVO, reloj())
    with pytest.raises(sqlite3.DatabaseError):
        reabrir(conn, c, dueno, MOTIVO, reloj())
    conn.close()

    assert (estado(db, p1), estado(db, p2), estado(db, c)) == (
        "PENDIENTE_VALIDACION", "PENDIENTE_VALIDACION", "CERRADA")
    assert "CONFIRMAR" not in acciones(db, p1) and "RECHAZAR" not in acciones(db, p2)
    assert "REABRIR" not in acciones(db, c)


# ----------------------------------------------------------------- S03
def test_pt26_s03_permisos_y_estados_incompatibles(ciclo, db):
    """PT-26 · AC-S03-04, 05, 06, 08, 09. Esperado: técnico no asignado registra → 403;
    coordinador y solicitante inician o registran → 403; estados incompatibles → 409;
    en todos los casos sin cambios de estado, soluciones ni historial."""
    a = ciclo.en_estado("EN_ATENCION")
    antes, sol_antes = acciones(db, a), contar(db, "soluciones")
    assert ciclo.solucion(a, S1, usuario="tecnico2") == 403
    for quien in ("coordinador1", "solicitante1"):
        assert ciclo.post(quien, f"/incidencias/{a}/iniciar") == 403, quien
        assert ciclo.solucion(a, S1, usuario=quien) == 403, quien
    assert estado(db, a) == "EN_ATENCION"
    assert acciones(db, a) == antes and contar(db, "soluciones") == sol_antes

    for est in ("REGISTRADA", "PENDIENTE_VALIDACION", "CERRADA"):         # registrar solución
        j = ciclo.en_estado(est)
        antes, sol_antes = acciones(db, j), contar(db, "soluciones")
        assert ciclo.solucion(j, S1) == 409, est
        assert estado(db, j) == est and acciones(db, j) == antes and contar(db, "soluciones") == sol_antes

    for est in ("REGISTRADA", "EN_ATENCION", "PENDIENTE_VALIDACION", "CERRADA"):   # iniciar
        j = ciclo.en_estado(est)
        antes = acciones(db, j)
        assert ciclo.post("tecnico1", f"/incidencias/{j}/iniciar") == 409, est
        assert estado(db, j) == est and acciones(db, j) == antes


def test_pt27_s03_limites_de_la_solucion(ciclo, db):
    """PT-27 · AC-S03-10, 11, 12. Esperado: 19, 19 con espacios externos y 801 → 400;
    20 → 200; 800 → 200 (guardada con 800 caracteres)."""
    a = ciclo.en_estado("EN_ATENCION")
    for texto in ("x" * 19, "  " + "x" * 19 + "  ", "x" * 801):
        assert ciclo.solucion(a, texto) == 400
    assert estado(db, a) == "EN_ATENCION"
    assert db.execute("SELECT COUNT(*) FROM soluciones WHERE incidencia_id=?", (a,)).fetchone()[0] == 0
    assert ciclo.solucion(a, "x" * 20) == 200

    b = ciclo.en_estado("EN_ATENCION")
    assert ciclo.solucion(b, "x" * 800) == 200
    largo = db.execute("SELECT length(texto) FROM soluciones WHERE incidencia_id=?", (b,)).fetchone()[0]
    assert largo == 800


def test_pt28_incidencia_inexistente_y_sin_sesion(ciclo, app, db):
    """PT-28 · AC-S03-13, 14, S04-16, S05-16. Esperado: id inexistente → 404;
    sin sesión → 302 al login en todas las rutas; sin efectos."""
    i = ciclo.en_estado("PENDIENTE_VALIDACION")
    antes = acciones(db, i)
    assert ciclo.post("tecnico1", "/incidencias/999/iniciar") == 404
    assert ciclo.solucion(999, S1) == 404
    assert ciclo.post("solicitante1", "/incidencias/999/confirmar") == 404
    assert ciclo.rechazar(999) == 404
    assert ciclo.reabrir(999) == 404
    assert ciclo.c("solicitante1").get("/incidencias/999").status_code == 404

    anonimo = app.test_client()
    rutas = [("post", f"/incidencias/{i}/iniciar"), ("post", f"/incidencias/{i}/solucion"),
             ("post", f"/incidencias/{i}/confirmar"), ("post", f"/incidencias/{i}/rechazar"),
             ("post", f"/incidencias/{i}/reabrir"), ("get", "/incidencias"),
             ("get", f"/incidencias/{i}"), ("get", "/tablero")]
    for metodo, ruta in rutas:
        r = getattr(anonimo, metodo)(ruta)
        assert r.status_code == 302 and "/login" in r.headers["Location"], ruta
    assert estado(db, i) == "PENDIENTE_VALIDACION" and acciones(db, i) == antes


# ----------------------------------------------------------------- S04
def test_pt29_s04_rechazar_y_reabrir_por_otras_personas(ciclo, db):
    """PT-29 · AC-S04-04, 05. Esperado: otro solicitante, coordinador y técnico → 403
    al rechazar y al reabrir; sin cambios."""
    p = ciclo.en_estado("PENDIENTE_VALIDACION")
    c = ciclo.en_estado("CERRADA")
    antes_p, antes_c = acciones(db, p), acciones(db, c)
    for quien in ("solicitante2", "coordinador1", "tecnico1"):
        assert ciclo.rechazar(p, usuario=quien) == 403, quien
        assert ciclo.reabrir(c, usuario=quien) == 403, quien
    assert estado(db, p) == "PENDIENTE_VALIDACION" and estado(db, c) == "CERRADA"
    assert acciones(db, p) == antes_p and acciones(db, c) == antes_c


def test_pt30_s04_estados_incompatibles(ciclo, db):
    """PT-30 · AC-S04-06, 07. Esperado: confirmar y rechazar fuera de PENDIENTE_VALIDACION → 409;
    reabrir fuera de CERRADA → 409; sin cambios."""
    for est in ("REGISTRADA", "ASIGNADA", "EN_ATENCION", "CERRADA"):
        j = ciclo.en_estado(est)
        antes = acciones(db, j)
        assert ciclo.post("solicitante1", f"/incidencias/{j}/confirmar") == 409, est
        assert ciclo.rechazar(j) == 409, est
        assert estado(db, j) == est and acciones(db, j) == antes
    for est in ("REGISTRADA", "ASIGNADA", "EN_ATENCION", "PENDIENTE_VALIDACION"):
        j = ciclo.en_estado(est)
        antes = acciones(db, j)
        assert ciclo.reabrir(j) == 409, est
        assert estado(db, j) == est and acciones(db, j) == antes


def test_pt31_s04_limites_del_motivo_en_rechazo_y_reapertura(ciclo, db):
    """PT-31 · AC-S04-08, 09. Esperado: 9 y 301 caracteres → 400; 10 y 300 → 200."""
    p = ciclo.en_estado("PENDIENTE_VALIDACION")
    c = ciclo.en_estado("CERRADA")
    assert ciclo.reabrir(c, "x" * 9) == 400
    assert ciclo.reabrir(c, "x" * 301) == 400
    assert ciclo.rechazar(p, "x" * 301) == 400
    assert estado(db, c) == "CERRADA" and estado(db, p) == "PENDIENTE_VALIDACION"
    assert ciclo.rechazar(p, "x" * 300) == 200 and estado(db, p) == "EN_ATENCION"
    assert ciclo.reabrir(c, "x" * 10) == 200 and estado(db, c) == "EN_ATENCION"


def test_pt32_s04_la_hora_la_pone_el_servidor(ciclo, db, reloj):
    """PT-32 · AC-S04-15. El cliente envía fechas falsas. Esperado: los eventos usan la hora
    del servidor (2026-10-13T12:00:00+00:00)."""
    falsos = {"creado_en": "1999-01-01T00:00:00+00:00", "fecha": "1999-01-01", "ahora": "1999-01-01"}
    p1 = ciclo.en_estado("PENDIENTE_VALIDACION")
    p2 = ciclo.en_estado("PENDIENTE_VALIDACION")
    c = ciclo.en_estado("CERRADA")
    assert ciclo.post("solicitante1", f"/incidencias/{p1}/confirmar", **falsos) == 200
    assert ciclo.rechazar(p2, **falsos) == 200
    assert ciclo.reabrir(c, **falsos) == 200
    for accion in ("RECHAZAR", "REABRIR"):
        fecha = db.execute("SELECT creado_en FROM eventos WHERE accion=?", (accion,)).fetchone()[0]
        assert fecha == "2026-10-13T12:00:00+00:00", accion
    ultimo = db.execute("SELECT creado_en FROM eventos WHERE incidencia_id=? AND accion='CONFIRMAR'", (p1,)).fetchone()[0]
    assert ultimo == "2026-10-13T12:00:00+00:00"


def test_pt33_texto_con_script_se_muestra_escapado_en_todas_las_vistas(ciclo, db, id_de):
    """PT-33 · AC-S03-15, S04-17, S05-17. Descripción, solución y motivo con <script>.
    Esperado: en listado, detalle, historial y pantalla del técnico aparece `&lt;script&gt;`
    y nunca `<script>alert(1)</script>`."""
    i = ciclo.nueva(descripcion=SCRIPT + " descripcion")
    assert ciclo.post("coordinador1", f"/incidencias/{i}/asignar", tecnico_id=id_de("tecnico1")) == 200
    assert ciclo.post("tecnico1", f"/incidencias/{i}/iniciar") == 200
    assert ciclo.solucion(i, SCRIPT + " solucion") == 200
    assert ciclo.rechazar(i, SCRIPT) == 200

    vistas = [ciclo.c("solicitante1").get(f"/incidencias/{i}"),
              ciclo.c("solicitante1").get("/incidencias"),
              ciclo.c("coordinador1").get("/incidencias"),
              ciclo.c("tecnico1").get("/atencion")]
    for r in vistas:
        html = r.get_data(as_text=True)
        assert r.status_code == 200
        assert "&lt;script&gt;" in html
        assert SCRIPT not in html


def test_pt34_orden_de_validaciones(ciclo, app, db, reloj):
    """PT-34 · AC-S03-19, S04-19, S05-21. Esperado, siempre sin efectos:
    S03: no asignado + 5 caracteres → 403; asignado + 5 caracteres en ASIGNADA → 409; sin sesión → 302.
    S04: no dueño + motivo corto → 403; dueño en ASIGNADA → 409; reabrir fuera de plazo con motivo corto → 400.
    S05: sin sesión → 302; id inexistente → 404; ajeno → 403."""
    a = ciclo.en_estado("ASIGNADA")
    assert ciclo.solucion(a, "12345", usuario="tecnico2") == 403
    assert ciclo.solucion(a, "12345", usuario="tecnico1") == 409
    anonimo = app.test_client()
    assert anonimo.post("/incidencias/999/solucion").status_code == 302

    assert ciclo.rechazar(a, "abc", usuario="solicitante2") == 403
    assert ciclo.rechazar(a, "abc", usuario="solicitante1") == 409
    c = ciclo.en_estado("CERRADA")
    reloj.avanzar(timedelta(hours=49))
    assert ciclo.reabrir(c, "abc") == 400
    assert estado(db, c) == "CERRADA" and estado(db, a) == "ASIGNADA"

    assert anonimo.get("/incidencias/999").status_code == 302
    assert ciclo.c("solicitante2").get("/incidencias/999").status_code == 404
    assert ciclo.c("solicitante2").get(f"/incidencias/{a}").status_code == 403


# ----------------------------------------------------------------- S05
def test_pt35_historial_completo_en_pantalla_con_desempate_por_id(ciclo, db, reloj, id_de):
    """PT-35 · AC-S04-13, S05-09, 20. Con el reloj quieto todos los eventos tienen la misma fecha.
    Esperado: el historial muestra los 8 eventos en orden de id, con soluciones y motivos."""
    i = ciclo.nueva()
    ciclo.post("coordinador1", f"/incidencias/{i}/asignar", tecnico_id=id_de("tecnico1"))
    ciclo.post("tecnico1", f"/incidencias/{i}/iniciar")
    ciclo.solucion(i, S1)
    ciclo.rechazar(i, "El daño sigue presente")
    ciclo.solucion(i, S2)
    ciclo.post("solicitante1", f"/incidencias/{i}/confirmar")
    ciclo.reabrir(i, "El daño volvió a aparecer")

    html = ciclo.c("solicitante1").get(f"/incidencias/{i}").get_data(as_text=True)
    historial = html.split("Historial</h2>")[1].split("Soluciones registradas")[0]
    mostrados = re.findall(r"<td>(CREAR|ASIGNAR|INICIAR|PROPONER_SOLUCION|CONFIRMAR|RECHAZAR|REABRIR)</td>", historial)
    assert mostrados == ["CREAR", "ASIGNAR", "INICIAR", "PROPONER_SOLUCION",
                         "RECHAZAR", "PROPONER_SOLUCION", "CONFIRMAR", "REABRIR"]
    for texto in (S1, S2, "El daño sigue presente", "El daño volvió a aparecer"):
        assert texto in html
    assert len(set(f[0] for f in db.execute("SELECT creado_en FROM eventos WHERE incidencia_id=?", (i,)))) == 1


def test_pt36_alcance_reciproco_y_filtros_combinados(ciclo):
    """PT-36 · AC-S05-01, 06. Esperado: A no ve lo de B ni B lo de A; estado+prioridad juntos."""
    a_normal = ciclo.nueva()
    a_critica = ciclo.nueva(riesgo_personas="true")
    a_critica_cerrada = ciclo.en_estado("CERRADA", riesgo_personas="true")
    b = ciclo.nueva(usuario="solicitante2")

    lista_a = ciclo.c("solicitante1").get("/incidencias").get_data(as_text=True)
    lista_b = ciclo.c("solicitante2").get("/incidencias").get_data(as_text=True)
    for i in (a_normal, a_critica, a_critica_cerrada):
        assert codigo(i) in lista_a and codigo(i) not in lista_b
    assert codigo(b) in lista_b and codigo(b) not in lista_a

    combinado = ciclo.c("solicitante1").get("/incidencias?estado=REGISTRADA&prioridad=CRITICA").get_data(as_text=True)
    assert codigo(a_critica) in combinado
    assert codigo(a_normal) not in combinado and codigo(a_critica_cerrada) not in combinado


def test_pt37_tablero_cantidades_por_estado_y_prioridad(ciclo):
    """PT-37 · AC-S05-12. Datos: REGISTRADA crítica, REGISTRADA normal, EN_ATENCION alta, CERRADA crítica.
    Esperado: estados 2/0/1/0/1; prioridades CRITICA 2, ALTA 1, NORMAL 1; críticas no cerradas 1; 25,0 %."""
    ciclo.nueva(riesgo_personas="true")
    ciclo.nueva()
    ciclo.en_estado("EN_ATENCION", impacto="ALTO")
    ciclo.en_estado("CERRADA", riesgo_personas="true")

    html = ciclo.c("coordinador1").get("/tablero").get_data(as_text=True)
    esperadas = ["<td>REGISTRADA</td><td>2</td>", "<td>ASIGNADA</td><td>0</td>", "<td>EN_ATENCION</td><td>1</td>",
                 "<td>PENDIENTE_VALIDACION</td><td>0</td>", "<td>CERRADA</td><td>1</td>",
                 "<td>CRITICA</td><td>2</td>", "<td>ALTA</td><td>1</td>", "<td>NORMAL</td><td>1</td>",
                 "<td>CRITICA no cerradas</td><td>1</td>", "<td>Porcentaje de cierre</td><td>25,0 %</td>"]
    for fragmento in esperadas:
        assert fragmento in html, fragmento


def test_pt38_reinicio_conserva_listado_historial_y_tablero(ciclo, ruta_db):
    """PT-38 · AC-S05-18. Esperado: tras 'reiniciar' (app nueva sobre el mismo archivo) el listado,
    el historial y el tablero muestran exactamente lo mismo."""
    i = ciclo.en_estado("CERRADA")
    antes = (ciclo.c("coordinador1").get("/incidencias").get_data(as_text=True),
             ciclo.c("solicitante1").get(f"/incidencias/{i}").get_data(as_text=True),
             ciclo.c("coordinador1").get("/tablero").get_data(as_text=True))

    nueva = create_app(ruta_db)
    nueva.config["TESTING"] = True

    def entrar(usuario):
        c = nueva.test_client()
        c.post("/login", data={"username": usuario, "password": CLAVES[usuario]})
        return c
    despues = (entrar("coordinador1").get("/incidencias").get_data(as_text=True),
               entrar("solicitante1").get(f"/incidencias/{i}").get_data(as_text=True),
               entrar("coordinador1").get("/tablero").get_data(as_text=True))
    assert despues == antes
    assert "100,0 %" in despues[2]          # 1 cerrada de 1 incidencia
