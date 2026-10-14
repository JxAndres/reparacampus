"""Fixtures compartidas de las pruebas de ReparaCampus.

- Cada prueba usa su PROPIA base SQLite temporal (copia de una base sembrada),
  nunca la base real de desarrollo.
- Las claves de las cuentas ficticias salen de app/seed.py (datos ficticios).
- El reloj es controlable: ninguna prueba espera tiempo real.
"""
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

import pytest

from app import create_app
from app.seed import sembrar

# Cuentas ficticias del seed (username -> clave)
CLAVES = {
    "solicitante1": "Clave-Demo-01",
    "solicitante2": "Clave-Demo-02",
    "coordinador1": "Clave-Demo-03",
    "tecnico1": "Clave-Demo-04",
    "tecnico2": "Clave-Demo-05",
}

# Datos válidos para registrar una incidencia (RF01)
DATOS_VALIDOS = {
    "ubicacion": "LAB-01",
    "categoria": "TIC",
    "descripcion": "La toma de corriente del laboratorio esta rota",
    "impacto": "BAJO",
    "riesgo_personas": "false",
}


@pytest.fixture(scope="session")
def base_sembrada(tmp_path_factory):
    """Base con esquema + 5 usuarios, creada una sola vez (el hash es lento)."""
    ruta = tmp_path_factory.mktemp("plantilla") / "plantilla.db"
    sembrar(str(ruta))
    return ruta


@pytest.fixture
def ruta_db(tmp_path, base_sembrada):
    """Copia independiente de la base para cada prueba."""
    destino = tmp_path / "prueba.db"
    shutil.copy(base_sembrada, destino)
    return str(destino)


@pytest.fixture
def app(ruta_db):
    aplicacion = create_app(ruta_db)
    aplicacion.config["TESTING"] = True
    return aplicacion


@pytest.fixture
def db(ruta_db):
    """Conexión de lectura para comprobar EFECTOS en la base de datos."""
    conn = sqlite3.connect(ruta_db)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def reloj(monkeypatch):
    """Reloj controlado (UTC). Uso: reloj.fijar(datetime(...)) o reloj.avanzar(timedelta).

    Los módulos hacen `from app.reloj import ahora`, así que parchear solo
    app.reloj.ahora NO bastaría: se reemplaza también en cada módulo app.* que
    tenga su propia referencia a `ahora`.
    """
    class RelojControlado:
        def __init__(self):
            self.actual = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)

        def fijar(self, momento):
            self.actual = momento

        def avanzar(self, delta):
            self.actual = self.actual + delta

        def __call__(self):
            return self.actual

    falso = RelojControlado()
    for nombre, modulo in list(sys.modules.items()):
        if nombre.startswith("app") and modulo is not None and hasattr(modulo, "ahora"):
            monkeypatch.setattr(modulo, "ahora", falso)
    return falso


@pytest.fixture
def cliente_de(app):
    """Fábrica de clientes ya autenticados: cliente_de("tecnico1")."""
    def _crear(username):
        cliente = app.test_client()
        r = cliente.post("/login", data={"username": username, "password": CLAVES[username]})
        assert r.status_code == 302, f"No se pudo iniciar sesión como {username}"
        return cliente
    return _crear


@pytest.fixture
def id_de(db):
    """id de un usuario del seed a partir de su username."""
    def _buscar(username):
        return db.execute("SELECT id FROM usuarios WHERE username = ?", (username,)).fetchone()["id"]
    return _buscar


@pytest.fixture
def registrar(cliente_de):
    """Registra una incidencia como solicitante1 (o el indicado). Devuelve la respuesta."""
    def _registrar(usuario="solicitante1", **cambios):
        datos = {**DATOS_VALIDOS, **cambios}
        return cliente_de(usuario).post("/incidencias", data=datos)
    return _registrar
