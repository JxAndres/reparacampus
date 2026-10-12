# ReparaCampus

Prototipo web para gestionar incidencias de infraestructura de la Universidad Simón Bolívar:
registrar reportes, priorizarlos, asignar técnico, atender y validar la solución.
Examen SDD + IA · Ingeniería de Software I. Todos los datos son ficticios.

## Versiones exactas

| Componente | Versión |
|---|---|
| Python | 3.15.0 |
| Git | 2.56.0 |
| Flask | 3.1.3 |
| Werkzeug | 3.1.9 |
| Jinja2 | 3.1.6 |
| pytest | 9.1.1 |
| SQLite | Incluido con Python (módulo `sqlite3`) |

Las dependencias completas están en `requirements.txt`.

## Instalación (desde una copia limpia)

Requisitos: Python 3.11 o superior y Git.

```powershell
git clone https://github.com/JxAndres/reparacampus.git
cd reparacampus
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

En Mac o Linux, el entorno se activa con `source .venv/bin/activate`.
Si PowerShell bloquea la activación, ejecute una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Base de datos y seed

El esquema está en `app/schema.sql`. La base `data/reparacampus.db` no se versiona;
se crea con el seed, que inserta las cinco cuentas ficticias:

```powershell
python -m app.seed
```

Debe imprimir `Seed listo: 5 usuarios en la base de datos.` Es seguro repetirlo:
no duplica usuarios.

## Arranque

```powershell
flask --app app run --debug
```

Abrir http://127.0.0.1:5000. Los datos permanecen al reiniciar el servidor.

## Cuentas ficticias

| Usuario | Contraseña | Rol |
|---|---|---|
| `solicitante1` | `Clave-Demo-01` | SOLICITANTE |
| `solicitante2` | `Clave-Demo-02` | SOLICITANTE |
| `coordinador1` | `Clave-Demo-03` | COORDINADOR |
| `tecnico1` | `Clave-Demo-04` | TECNICO |
| `tecnico2` | `Clave-Demo-05` | TECNICO |

Las contraseñas se guardan con hash (scrypt, vía Werkzeug). Son datos de demostración.

## Pruebas

```powershell
python -m pytest -v
```

Las pruebas viven en `tests/` y usan una base de datos independiente de la de
desarrollo. Cada reporte de ejecución debe registrar comando, fecha, datos,
resultado y SHA del commit.

## Estructura

```
app/
  __init__.py        fábrica de la aplicación (create_app)
  auth.py            login, logout, sesión y decorador de roles
  incidencias.py     registrar incidencias (S01)
  asignaciones.py    asignar técnico (S02)
  prioridad.py       cálculo de prioridad (función pura)
  reloj.py           reloj del servidor, reemplazable en pruebas
  db.py              conexión SQLite
  schema.sql         esquema de la base de datos
  seed.py            cuentas ficticias
  templates/         plantillas Jinja
specs/               especificaciones S01 a S05 y preguntas al cliente
docs/                diseño, diagramas y bitácora de IA
tests/               pruebas pytest
```

## Estado de las funcionalidades

| Spec | Requisito | Estado |
|---|---|---|
| S01 | RF01 Registrar | Implementada |
| S02 | RF02 Priorizar y asignar | Implementada |
| S03 | RF03 Atender | Pendiente |
| S04 | RF04 Validar | Pendiente |
| S05 | RF05 Consultar e historizar | Pendiente |

## Reglas de diseño

- La identidad y el rol salen siempre de la sesión del servidor.
- La prioridad se calcula (riesgo + impacto) y no se guarda ni la envía el cliente.
- Cada operación guarda el cambio de estado y su evento en una sola transacción.
- El historial (`eventos`) no se puede modificar ni borrar: lo impiden triggers de SQLite.
- Los textos se escapan al mostrarse; no se ejecutan como HTML ni scripts.

## Entrega

- Repositorio: https://github.com/JxAndres/reparacampus
- Tablero: https://github.com/users/JxAndres/projects/1
- Tag de entrega: `release-examen` (pendiente)
- SHA final: (pendiente)

## Limitaciones conocidas

- Las respuestas del cliente a las preguntas P1 a P3 están pendientes (ver `specs/00-preguntas-y-supuestos.md`).
- Funcionalidades S03, S04 y S05 y sus pruebas automatizadas: pendientes al momento de esta versión.
- La clave de sesión (`SECRET_KEY`) tiene un valor de desarrollo por defecto; en un entorno real debe definirse por variable de entorno.
- Prototipo sin adjuntos, notificaciones ni hosting, según el alcance del examen.