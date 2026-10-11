PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    nombre        TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('SOLICITANTE', 'COORDINADOR', 'TECNICO')),
    password_hash TEXT NOT NULL,
    activo        INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS incidencias (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT UNIQUE,
    ubicacion       TEXT NOT NULL CHECK (ubicacion IN ('LAB-01', 'AULA-201', 'BIB-01')),
    categoria       TEXT NOT NULL CHECK (categoria IN ('ELECTRICIDAD', 'HIDRAULICA', 'MOBILIARIO', 'TIC')),
    descripcion     TEXT NOT NULL CHECK (length(descripcion) BETWEEN 20 AND 500),
    impacto         TEXT NOT NULL CHECK (impacto IN ('BAJO', 'ALTO')),
    riesgo_personas INTEGER NOT NULL CHECK (riesgo_personas IN (0, 1)),
    estado          TEXT NOT NULL DEFAULT 'REGISTRADA' CHECK (estado IN (
                        'REGISTRADA', 'ASIGNADA', 'EN_ATENCION',
                        'PENDIENTE_VALIDACION', 'CERRADA')),
    autor_id        INTEGER NOT NULL REFERENCES usuarios(id),
    creada_en       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS asignaciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    incidencia_id   INTEGER NOT NULL UNIQUE REFERENCES incidencias(id),
    tecnico_id      INTEGER NOT NULL REFERENCES usuarios(id),
    coordinador_id  INTEGER NOT NULL REFERENCES usuarios(id),
    asignada_en     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS soluciones (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    incidencia_id  INTEGER NOT NULL REFERENCES incidencias(id),
    tecnico_id     INTEGER NOT NULL REFERENCES usuarios(id),
    texto          TEXT NOT NULL CHECK (length(texto) BETWEEN 20 AND 800),
    registrada_en  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eventos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    incidencia_id    INTEGER NOT NULL REFERENCES incidencias(id),
    accion           TEXT NOT NULL CHECK (accion IN (
                        'CREAR', 'ASIGNAR', 'INICIAR', 'PROPONER_SOLUCION',
                        'CONFIRMAR', 'RECHAZAR', 'REABRIR')),
    autor_id         INTEGER NOT NULL REFERENCES usuarios(id),
    estado_anterior  TEXT,
    estado_nuevo     TEXT NOT NULL,
    detalle          TEXT,
    creado_en        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_incidencias_estado ON incidencias(estado);
CREATE INDEX IF NOT EXISTS idx_incidencias_autor ON incidencias(autor_id);
CREATE INDEX IF NOT EXISTS idx_eventos_incidencia ON eventos(incidencia_id);

-- El historial no se puede editar ni borrar (RF05)
CREATE TRIGGER IF NOT EXISTS eventos_no_update
BEFORE UPDATE ON eventos
BEGIN
    SELECT RAISE(ABORT, 'El historial no se puede modificar');
END;

CREATE TRIGGER IF NOT EXISTS eventos_no_delete
BEFORE DELETE ON eventos
BEGIN
    SELECT RAISE(ABORT, 'El historial no se puede borrar');
END;