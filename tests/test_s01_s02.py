"""Pruebas de S01 (registrar) y S02 (priorizar y asignar).

Regla del examen: los valores ESPERADOS están escritos a mano antes de ejecutar;
no se calculan con funciones de producción.
Cada prueba indica su ID (PT-xx) y los AC de la SPEC que verifica.
"""
import sqlite3
from datetime import datetime, timezone

import pytest

from app.incidencias import crear_incidencia, validar_incidencia
from app.prioridad import calcular_prioridad
from tests.conftest import DATOS_VALIDOS


def contar(db, tabla):
    return db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


# ---------------------------------------------------------------- S01 / RF01
def test_pt01_registro_valido_crea_incidencia_y_evento(registrar, db, reloj, id_de):
    """PT-01 · AC-S01-01 · Entrada válida.
    Esperado: 201, código INC-0001, REGISTRADA, autor=solicitante1, fecha=reloj,
    y exactamente un evento CREAR (anterior NULL -> REGISTRADA)."""
    r = registrar()

    assert r.status_code == 201
    inc = db.execute("SELECT * FROM incidencias").fetchone()
    assert inc["codigo"] == "INC-0001"
    assert inc["estado"] == "REGISTRADA"
    assert inc["autor_id"] == id_de("solicitante1")
    assert inc["creada_en"] == "2026-10-13T12:00:00+00:00"
    eventos = db.execute("SELECT * FROM eventos").fetchall()
    assert len(eventos) == 1
    assert eventos[0]["accion"] == "CREAR"
    assert eventos[0]["estado_anterior"] is None
    assert eventos[0]["estado_nuevo"] == "REGISTRADA"
    assert eventos[0]["autor_id"] == id_de("solicitante1")


def test_pt02_limite_descripcion_19_y_20_con_espacios(registrar, db):
    """PT-02 · AC-S01-04, AC-S01-06 · Límites de la descripción.
    Esperado: 19 -> 400 sin guardar; 19 útiles + espacios externos -> 400;
    20 -> 201 y queda guardada (recortada)."""
    assert registrar(descripcion="x" * 19).status_code == 400
    assert registrar(descripcion="   " + "x" * 19 + "   ").status_code == 400
    assert contar(db, "incidencias") == 0
    assert contar(db, "eventos") == 0

    assert registrar(descripcion="x" * 20).status_code == 201
    assert contar(db, "incidencias") == 1
    assert db.execute("SELECT descripcion FROM incidencias").fetchone()[0] == "x" * 20


@pytest.mark.parametrize("campo,valor", [
    ("impacto", "MEDIO"),            # fuera de BAJO/ALTO
    ("riesgo_personas", "talvez"),   # no booleano
    ("ubicacion", "PATIO-9"),        # fuera de la lista
    ("categoria", "JARDINERIA"),     # fuera de la lista
    ("ubicacion", ""),               # campo vacío
])
def test_pt03_valores_invalidos_se_rechazan_sin_efectos(registrar, db, campo, valor):
    """PT-03 · AC-S01-03 · Valores inválidos.
    Esperado: 400 y no se crea incidencia ni evento."""
    r = registrar(**{campo: valor})

    assert r.status_code == 400
    assert contar(db, "incidencias") == 0
    assert contar(db, "eventos") == 0


def test_pt04_roles_no_solicitante_no_pueden_registrar(cliente_de, app, db):
    """PT-04 · AC-S01-02, AC-S01-07 · Permisos de registro.
    Esperado: coordinador y técnico -> 403; visitante sin sesión -> 302 a /login."""
    for usuario in ("coordinador1", "tecnico1"):
        r = cliente_de(usuario).post("/incidencias", data=DATOS_VALIDOS)
        assert r.status_code == 403, usuario
    r = app.test_client().post("/incidencias", data=DATOS_VALIDOS)
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]
    assert contar(db, "incidencias") == 0
    assert contar(db, "eventos") == 0


def test_pt05_atomicidad_fallo_al_guardar_evento_no_deja_incidencia(ruta_db, db, id_de):
    """PT-05 · AC-S01-09 · Estado e historial se guardan juntos.
    Se instala un trigger que hace fallar el INSERT en eventos.
    Esperado: la operación falla y NO queda ninguna incidencia huérfana."""
    conn = sqlite3.connect(ruta_db)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TRIGGER falla_evento BEFORE INSERT ON eventos "
        "BEGIN SELECT RAISE(ABORT, 'fallo simulado'); END;"
    )
    conn.commit()
    datos, errores = validar_incidencia(DATOS_VALIDOS)
    assert errores == []

    with pytest.raises(sqlite3.DatabaseError):
        crear_incidencia(conn, id_de("solicitante1"), datos,
                         datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc))
    conn.close()

    assert contar(db, "incidencias") == 0
    assert contar(db, "eventos") == 0


# ---------------------------------------------------------------- S02 / RF02
@pytest.mark.parametrize("riesgo,impacto,esperada", [
    (True, "BAJO", "CRITICA"),    # AC-S02-01: el riesgo manda
    (True, "ALTO", "CRITICA"),    # AC-S02-01
    (False, "ALTO", "ALTA"),      # AC-S02-02
    (False, "BAJO", "NORMAL"),    # AC-S02-03
])
def test_pt06_prioridad_segun_riesgo_e_impacto(riesgo, impacto, esperada):
    """PT-06 · AC-S02-01, 02, 03 · Esperado: tabla de RF02 escrita a mano."""
    assert calcular_prioridad(riesgo, impacto) == esperada


def test_pt07_asignacion_correcta_y_repetida_conserva_tecnico(registrar, cliente_de, db, id_de):
    """PT-07 · AC-S02-04, AC-S02-06 · Asignación correcta y repetida.
    Esperado: 1ª asignación -> ASIGNADA con tecnico1 y evento ASIGNAR;
    2ª (otro técnico) -> 409 y todo queda igual (técnico, estado, historial)."""
    registrar()
    coordinador = cliente_de("coordinador1")

    r1 = coordinador.post("/incidencias/1/asignar", data={"tecnico_id": id_de("tecnico1")})
    assert r1.status_code == 200
    assert db.execute("SELECT estado FROM incidencias WHERE id=1").fetchone()[0] == "ASIGNADA"
    asig = db.execute("SELECT * FROM asignaciones WHERE incidencia_id=1").fetchone()
    assert asig["tecnico_id"] == id_de("tecnico1")
    assert asig["coordinador_id"] == id_de("coordinador1")
    acciones = [e["accion"] for e in db.execute("SELECT accion FROM eventos ORDER BY id")]
    assert acciones == ["CREAR", "ASIGNAR"]

    r2 = coordinador.post("/incidencias/1/asignar", data={"tecnico_id": id_de("tecnico2")})
    assert r2.status_code == 409
    assert db.execute("SELECT tecnico_id FROM asignaciones WHERE incidencia_id=1").fetchone()[0] == id_de("tecnico1")
    assert contar(db, "asignaciones") == 1
    assert [e["accion"] for e in db.execute("SELECT accion FROM eventos ORDER BY id")] == ["CREAR", "ASIGNAR"]


def test_pt08_permisos_y_tecnico_invalido_en_asignacion(registrar, cliente_de, db, id_de):
    """PT-08 · AC-S02-05, AC-S02-07 · Permisos y técnico inválido.
    Esperado: solicitante y técnico -> 403; técnico inexistente o con rol
    SOLICITANTE -> 422; la incidencia sigue REGISTRADA sin asignación."""
    registrar()
    tecnico = id_de("tecnico1")

    assert cliente_de("solicitante1").post("/incidencias/1/asignar", data={"tecnico_id": tecnico}).status_code == 403
    assert cliente_de("tecnico1").post("/incidencias/1/asignar", data={"tecnico_id": tecnico}).status_code == 403

    coordinador = cliente_de("coordinador1")
    assert coordinador.post("/incidencias/1/asignar", data={"tecnico_id": 999}).status_code == 422
    assert coordinador.post("/incidencias/1/asignar", data={"tecnico_id": id_de("solicitante2")}).status_code == 422

    assert db.execute("SELECT estado FROM incidencias WHERE id=1").fetchone()[0] == "REGISTRADA"
    assert contar(db, "asignaciones") == 0
    assert contar(db, "eventos") == 1  # solo el CREAR


# ------------------------------------------------- Persistencia / seguridad
def test_pt09_texto_html_se_muestra_escapado(registrar, cliente_de):
    """PT-09 · AC-S01-08 · Texto parecido a HTML no se ejecuta.
    Esperado: en la pantalla del coordinador aparece &lt;script&gt; y nunca <script>."""
    registrar(descripcion="<script>alert(1)</script> falla")

    html = cliente_de("coordinador1").get("/asignaciones").get_data(as_text=True)

    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_pt10_reinicio_conserva_datos(registrar, ruta_db):
    """PT-10 · Persistencia · Un 'reinicio' = crear una app nueva sobre el mismo archivo.
    Esperado: la incidencia y su evento siguen ahí."""
    from app import create_app
    registrar()

    conn = sqlite3.connect(ruta_db)
    assert conn.execute("SELECT COUNT(*) FROM incidencias").fetchone()[0] == 1
    conn.close()

    app_nueva = create_app(ruta_db)
    app_nueva.config["TESTING"] = True
    from tests.conftest import CLAVES
    c = app_nueva.test_client()
    c.post("/login", data={"username": "coordinador1", "password": CLAVES["coordinador1"]})
    html = c.get("/asignaciones").get_data(as_text=True)
    assert "INC-0001" in html
