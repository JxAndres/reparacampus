from datetime import datetime, timezone

from werkzeug.security import generate_password_hash

from app.db import init_db

# Cuentas ficticias de prueba. No son datos reales.
USUARIOS = [
    ("solicitante1", "Laura Solicitante", "SOLICITANTE", "Clave-Demo-01"),
    ("solicitante2", "Pedro Solicitante", "SOLICITANTE", "Clave-Demo-02"),
    ("coordinador1", "Marta Coordinadora", "COORDINADOR", "Clave-Demo-03"),
    ("tecnico1", "Tomás Técnico", "TECNICO", "Clave-Demo-04"),
    ("tecnico2", "Teresa Técnica", "TECNICO", "Clave-Demo-05"),
]


def sembrar(db_path=None):
    conn = init_db(db_path)
    for username, nombre, rol, clave in USUARIOS:
        conn.execute(
            "INSERT OR IGNORE INTO usuarios (username, nombre, rol, password_hash, activo) "
            "VALUES (?, ?, ?, ?, 1)",
            (username, nombre, rol, generate_password_hash(clave)),
        )
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    conn.close()
    return total


if __name__ == "__main__":
    n = sembrar()
    print(f"Seed listo: {n} usuarios en la base de datos.")