"""Pruebas de S03 (atender), S04 (validar) y S05 (consultar), con las 3 de integración.

Los valores ESPERADOS están escritos a mano antes de ejecutar (no se calculan con
funciones de producción). El reloj es controlado: no se espera tiempo real.
Las pruebas de integración usan la base SQLite REAL (archivo temporal), no mocks.
"""
import sqlite3
from datetime import timedelta

import pytest

from app.consultas import porcentaje_cierre

SOLUCION_1 = "Se reemplazo el cable danado y se probo la toma"
SOLUCION_2 = "Se cambio la regleta completa y se midio el voltaje"
MOTIVO_RECHAZO = "El daño sigue presente"


# ------------------------------------------------------------------ ayudas
def acciones(db, incidencia_id=1):
    return [f["accion"] for f in db.execute(
        "SELECT accion FROM eventos WHERE incidencia_id=? ORDER BY id", (incidencia_id,))]


def estado(db, incidencia_id=1):
    return db.execute("SELECT estado FROM incidencias WHERE id=?", (incidencia_id,)).fetchone()[0]


def contar(db, tabla):
    return db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


@pytest.fixture
def flujo(registrar, cliente_de, id_de, db):
    """Acciones del recorrido completo; cada una devuelve el código HTTP."""
    class Flujo:
        sol = cliente_de("solicitante1")
        coord = cliente_de("coordinador1")
        tec = cliente_de("tecnico1")

        def registrar(self, **cambios):
            assert registrar(**cambios).status_code == 201
            return db.execute("SELECT MAX(id) FROM incidencias").fetchone()[0]

        def asignar(self, i):
            return self.coord.post(f"/incidencias/{i}/asignar", data={"tecnico_id": id_de("tecnico1")}).status_code

        def iniciar(self, i):
            return self.tec.post(f"/incidencias/{i}/iniciar").status_code

        def proponer(self, i, texto=SOLUCION_1):
            return self.tec.post(f"/incidencias/{i}/solucion", data={"solucion": texto}).status_code

        def confirmar(self, i):
            return self.sol.post(f"/incidencias/{i}/confirmar").status_code

        def rechazar(self, i, motivo=MOTIVO_RECHAZO):
            return self.sol.post(f"/incidencias/{i}/rechazar", data={"motivo": motivo}).status_code

        def reabrir(self, i, motivo="El daño volvió a aparecer"):
            return self.sol.post(f"/incidencias/{i}/reabrir", data={"motivo": motivo}).status_code

        def hasta_pendiente(self):
            i = self.registrar()
            assert (self.asignar(i), self.iniciar(i), self.proponer(i)) == (200, 200, 200)
            return i

        def hasta_cerrada(self):
            i = self.hasta_pendiente()
            assert self.confirmar(i) == 200
            return i
    return Flujo()


# ------------------------------------------------- INTEGRACIÓN (3, base real)
def test_pt11_integracion_flujo_de_cierre(flujo, db, id_de):
    """PT-11 · INTEGRACIÓN · AC-S01-01, S02-04, S03-01/02, S04-01.
    Registrar → asignar → iniciar → proponer → confirmar.
    Esperado: estados REGISTRADA→ASIGNADA→EN_ATENCION→PENDIENTE_VALIDACION→CERRADA;
    eventos en ese orden; 1 solución; técnico tecnico1 en todo el recorrido."""
    i = flujo.registrar()
    assert estado(db, i) == "REGISTRADA"
    assert flujo.asignar(i) == 200 and estado(db, i) == "ASIGNADA"
    assert flujo.iniciar(i) == 200 and estado(db, i) == "EN_ATENCION"
    assert flujo.proponer(i) == 200 and estado(db, i) == "PENDIENTE_VALIDACION"
    assert flujo.confirmar(i) == 200 and estado(db, i) == "CERRADA"

    assert acciones(db, i) == ["CREAR", "ASIGNAR", "INICIAR", "PROPONER_SOLUCION", "CONFIRMAR"]
    assert contar(db, "soluciones") == 1
    assert db.execute("SELECT texto FROM soluciones").fetchone()[0] == SOLUCION_1
    assert db.execute("SELECT tecnico_id FROM asignaciones").fetchone()[0] == id_de("tecnico1")
    cierre = db.execute("SELECT * FROM eventos WHERE accion='CONFIRMAR'").fetchone()
    assert cierre["autor_id"] == id_de("solicitante1")
    assert (cierre["estado_anterior"], cierre["estado_nuevo"]) == ("PENDIENTE_VALIDACION", "CERRADA")


def test_pt12_integracion_rechazo_y_nueva_solucion(flujo, db, reloj, id_de):
    """PT-12 · INTEGRACIÓN · AC-S04-02, AC-S03-17.
    Rechazo → conserva técnico y solución anterior, registra quién, cuándo y por qué;
    luego nueva solución. Esperado: 2 soluciones, mismo técnico, eventos en orden."""
    i = flujo.hasta_pendiente()

    assert flujo.rechazar(i) == 200
    assert estado(db, i) == "EN_ATENCION"
    assert db.execute("SELECT tecnico_id FROM asignaciones").fetchone()[0] == id_de("tecnico1")
    assert [s["texto"] for s in db.execute("SELECT texto FROM soluciones")] == [SOLUCION_1]
    ev = db.execute("SELECT * FROM eventos WHERE accion='RECHAZAR'").fetchone()
    assert ev["autor_id"] == id_de("solicitante1")
    assert ev["detalle"] == MOTIVO_RECHAZO
    assert ev["creado_en"] == "2026-10-13T12:00:00+00:00"
    assert (ev["estado_anterior"], ev["estado_nuevo"]) == ("PENDIENTE_VALIDACION", "EN_ATENCION")

    assert flujo.proponer(i, SOLUCION_2) == 200
    assert estado(db, i) == "PENDIENTE_VALIDACION"
    assert [s["texto"] for s in db.execute("SELECT texto FROM soluciones ORDER BY id")] == [SOLUCION_1, SOLUCION_2]
    assert acciones(db, i) == ["CREAR", "ASIGNAR", "INICIAR", "PROPONER_SOLUCION",
                               "RECHAZAR", "PROPONER_SOLUCION"]


def test_pt13_integracion_cierre_reapertura_nueva_solucion_nuevo_cierre(flujo, db, reloj, id_de):
    """PT-13 · INTEGRACIÓN · AC-S04-03, 13, S03-18.
    Cierra, reabre a las 47 h, nueva solución, nuevo cierre.
    Esperado: 2 cierres y 2 soluciones conservados, mismo técnico, 8 eventos en orden."""
    i = flujo.hasta_cerrada()
    reloj.avanzar(timedelta(hours=47))

    assert flujo.reabrir(i) == 200
    assert estado(db, i) == "EN_ATENCION"
    assert flujo.proponer(i, SOLUCION_2) == 200
    reloj.avanzar(timedelta(hours=1))
    assert flujo.confirmar(i) == 200
    assert estado(db, i) == "CERRADA"

    assert acciones(db, i) == ["CREAR", "ASIGNAR", "INICIAR", "PROPONER_SOLUCION", "CONFIRMAR",
                               "REABRIR", "PROPONER_SOLUCION", "CONFIRMAR"]
    assert contar(db, "soluciones") == 2
    cierres = [e["creado_en"] for e in db.execute("SELECT creado_en FROM eventos WHERE accion='CONFIRMAR' ORDER BY id")]
    assert cierres == ["2026-10-13T12:00:00+00:00", "2026-10-15T12:00:00+00:00"]
    assert db.execute("SELECT detalle FROM eventos WHERE accion='REABRIR'").fetchone()[0] == "El daño volvió a aparecer"
    assert db.execute("SELECT tecnico_id FROM asignaciones").fetchone()[0] == id_de("tecnico1")


# ------------------------------------------------------------ S04 · plazo
def test_pt14_reapertura_exacta_48h_se_acepta_y_48h_mas_1s_se_rechaza(flujo, db, reloj):
    """PT-14 · AC-S04-11, AC-S04-12 · Límite de 48 horas con reloj controlado.
    Esperado: a las 48:00:00 → 200 EN_ATENCION; a las 48:00:01 → 409 y nada cambia."""
    a = flujo.hasta_cerrada()
    b = flujo.hasta_cerrada()           # mismo instante de cierre (reloj quieto)
    reloj.avanzar(timedelta(hours=48))
    assert flujo.reabrir(a) == 200
    assert estado(db, a) == "EN_ATENCION"

    reloj.avanzar(timedelta(seconds=1))
    eventos_antes = acciones(db, b)
    assert flujo.reabrir(b) == 409
    assert estado(db, b) == "CERRADA"
    assert acciones(db, b) == eventos_antes
    assert "REABRIR" not in eventos_antes


def test_pt15_plazo_se_cuenta_desde_el_ultimo_cierre(flujo, db, reloj):
    """PT-15 · AC-S04-14. Cierre en t0, reabre a t0+40h, cierra de nuevo a t0+50h.
    Esperado: a t0+50h+47h (97 h tras el 1er cierre, 47 h tras el último) SÍ reabre."""
    i = flujo.hasta_cerrada()
    reloj.avanzar(timedelta(hours=40))
    assert flujo.reabrir(i) == 200
    assert flujo.proponer(i, SOLUCION_2) == 200
    reloj.avanzar(timedelta(hours=10))
    assert flujo.confirmar(i) == 200

    reloj.avanzar(timedelta(hours=47))
    assert flujo.reabrir(i, "Otra vez fallando hoy") == 200
    assert estado(db, i) == "EN_ATENCION"


# --------------------------------------------------- permisos y sin efectos
def test_pt16_permisos_y_estados_incompatibles_sin_efectos(flujo, db, registrar, cliente_de):
    """PT-16 · AC-S03-03, 07, S04-04, S05-08. Esperado, sin cambios en estado ni historial:
    técnico no asignado inicia → 403; solución antes de iniciar → 409;
    otro solicitante / coordinador / técnico confirma → 403; otro solicitante lee → 403."""
    i = flujo.registrar()
    flujo.asignar(i)
    eventos = acciones(db, i)

    assert cliente_de("tecnico2").post(f"/incidencias/{i}/iniciar").status_code == 403
    assert flujo.proponer(i) == 409                       # sin iniciar
    assert estado(db, i) == "ASIGNADA"
    assert contar(db, "soluciones") == 0

    flujo.iniciar(i); flujo.proponer(i)
    eventos = acciones(db, i)
    for quien in ("solicitante2", "coordinador1", "tecnico1"):
        assert cliente_de(quien).post(f"/incidencias/{i}/confirmar").status_code == 403, quien
    assert estado(db, i) == "PENDIENTE_VALIDACION"
    assert acciones(db, i) == eventos

    assert cliente_de("solicitante2").get(f"/incidencias/{i}").status_code == 403
    assert cliente_de("solicitante1").get("/incidencias/999").status_code == 404


def test_pt17_motivo_invalido_no_deja_efectos(flujo, db):
    """PT-17 · AC-S04-08, AC-S05-11. Motivo de 9 caracteres → 400 y el historial no cambia;
    de 10 caracteres → 200."""
    i = flujo.hasta_pendiente()
    eventos = acciones(db, i)

    assert flujo.rechazar(i, "x" * 9) == 400
    assert flujo.rechazar(i, "  " + "x" * 9 + "  ") == 400     # espacios externos no cuentan
    assert estado(db, i) == "PENDIENTE_VALIDACION"
    assert acciones(db, i) == eventos

    assert flujo.rechazar(i, "x" * 10) == 200
    assert estado(db, i) == "EN_ATENCION"


# ---------------------------------------------------------------- S05
def test_pt18_tablero_vacio_25_por_ciento_y_reapertura(flujo, cliente_de, db):
    """PT-18 · AC-S05-12, 13, 14, 15. Tablero: vacío = 0,0 %; uno cerrado de cuatro = 25,0 %;
    reabrirlo → 0,0 % y el cierre anterior sigue en el historial. Solicitante → 403."""
    coord = cliente_de("coordinador1")
    assert "0,0 %" in coord.get("/tablero").get_data(as_text=True)

    cerrada = flujo.hasta_cerrada()
    for _ in range(3):
        flujo.registrar()
    assert "25,0 %" in coord.get("/tablero").get_data(as_text=True)

    assert flujo.reabrir(cerrada) == 200
    html = coord.get("/tablero").get_data(as_text=True)
    assert "0,0 %" in html and "25,0 %" not in html
    assert contar(db, "eventos WHERE accion='CONFIRMAR'") == 1     # cierre conservado

    assert cliente_de("solicitante1").get("/tablero").status_code == 403
    assert cliente_de("tecnico1").get("/tablero").status_code == 403


@pytest.mark.parametrize("cerradas,total,esperado", [
    (0, 0, "0,0 %"),     # sin registros, sin división por cero
    (1, 4, "25,0 %"),
    (1, 16, "6,3 %"),    # 6,25 → half-up (round() de Python daría 6,2)
    (1, 3, "33,3 %"),
])
def test_pt19_porcentaje_de_cierre(cerradas, total, esperado):
    """PT-19 · AC-S05-13, 19. Esperado escrito a mano."""
    assert porcentaje_cierre(cerradas, total) == esperado


def test_pt20_alcance_por_rol_y_filtros(flujo, cliente_de, db):
    """PT-20 · AC-S05-01, 02, 03, 04, 05, 07. Alcance por rol y filtros.
    Esperado: solicitante2 no ve nada ajeno; técnico2 no ve lo asignado a técnico1;
    coordinador ve las 2; filtro CERRADA y CRITICA correctos; filtro inválido → 400."""
    cerrada = flujo.hasta_cerrada()                       # riesgo false, BAJO → NORMAL
    critica = flujo.registrar(riesgo_personas="true")     # CRITICA, REGISTRADA

    html_coord = cliente_de("coordinador1").get("/incidencias").get_data(as_text=True)
    assert "INC-0001" in html_coord and "INC-0002" in html_coord

    assert "INC-0001" not in cliente_de("solicitante2").get("/incidencias").get_data(as_text=True)
    assert "INC-0001" not in cliente_de("tecnico2").get("/incidencias").get_data(as_text=True)
    assert "INC-0001" in cliente_de("tecnico1").get("/incidencias").get_data(as_text=True)

    solo_cerradas = cliente_de("coordinador1").get("/incidencias?estado=CERRADA").get_data(as_text=True)
    assert "INC-0001" in solo_cerradas and "INC-0002" not in solo_cerradas
    solo_criticas = cliente_de("coordinador1").get("/incidencias?prioridad=CRITICA").get_data(as_text=True)
    assert "INC-0002" in solo_criticas and "INC-0001" not in solo_criticas

    assert cliente_de("coordinador1").get("/incidencias?estado=ABIERTA").status_code == 400
    assert cliente_de("coordinador1").get("/incidencias?prioridad=URGENTE").status_code == 400


def test_pt21_historial_es_inmutable_en_la_base(flujo, db, ruta_db):
    """PT-21 · AC-S05-10. UPDATE y DELETE sobre eventos deben ser rechazados por la base.
    Esperado: sqlite lanza error y el evento permanece igual."""
    i = flujo.registrar()
    conn = sqlite3.connect(ruta_db)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE eventos SET accion='ASIGNAR' WHERE incidencia_id=?", (i,))
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM eventos WHERE incidencia_id=?", (i,))
    conn.close()
    assert acciones(db, i) == ["CREAR"]
