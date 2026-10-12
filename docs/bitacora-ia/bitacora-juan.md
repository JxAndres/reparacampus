# Bitácora de IA · Juan (JxAndres)

## Intervención 1: código de S01 (registrar incidencia)

| Campo | Registro |
|---|---|
| Fecha | 2026-10-11 |
| Autor | Juan (JxAndres) |
| Herramienta / modelo | Claude, en claude.ai Sonnet 5.5 Medio |
| Historia y SPEC / versión | S01 v0.1 (RF01), aprobada en el PR #1 |
| Archivos | `app/incidencias.py`, `app/reloj.py`, `app/templates/nueva.html` |
| Commit / PR | `ade648b`, PR #7 (revisado por Sebastián) |

### Objetivo y contexto
Implementar RF01 sobre la base Flask ya existente (login, sesión y decorador de roles),
el esquema SQL con el seed y la SPEC S01, que ya estaba versionada en `specs/`.

### Instrucción
Resumen: No hubo un prompt dirigido a esta tarea. S01 en código estaba asignada a que lo desarrollara Juan en el reparto de trabajo. Al terminar la base Flask, la IA propuso continuar con S01 usando
la SPEC S01 v0.1, el esquema SQL y la base ya existentes, y entregó el código y una
tabla de pruebas. Juan aceptó el enfoque y pasó a verificarlo.

Limitación de proceso: la instrucción no fue un pedido siguiendo criterios (por
ejemplo "implementa solo AC-S01-01 y AC-S01-02"), como recomienda el enunciado.

### Respuesta relevante
Claude propuso tres piezas: una función de validación que recorta espacios antes de medir
longitudes, una función `crear_incidencia` con transacción única (incidencia, código y
evento CREAR) y un reloj `ahora()` separado para poder controlarlo en pruebas. El autor
sale de la sesión, no del formulario.

### Decisión humana y justificación
- **Aceptado:** estructura de tres funciones y transacción única, porque cumple S01 y
  permite probar la validación sin navegador.
- **Aceptado tras comprobar:** el reloj separado, porque S04 necesita controlar las 48 h.
- **Decisión propia:** Decisión aceptada: la IA recomendó identificar por id entero y mostrar INC-0001 solo como etiqueta; Juan la aceptó y la comunicó al equipo.

### Error o limitación
- Los criterios AC-S01-03 (valores inválidos como impacto "MEDIO") y AC-S01-09 (atomicidad
  ante fallo) no se pueden provocar desde el formulario, que solo ofrece opciones válidas.
  Quedan para pytest.
- En un paso previo de la misma sesión, los archivos `schema.sql`, `db.py` y `seed.py`
  quedaron con tamaño 0 Lo detectó Juan al ejecutar el seed sin salida; se corrigió con Get-ChildItem y, se corrigió guardando cada archivo y se verificó con elseed (5 usuarios).

### Corrección y verificación
Prueba manual con datos fijos y consulta a la base:

| Caso | Resultado | AC |
|---|---|---|
| Descripción válida | Se creó INC-0001 | S01-01 |
| 19 caracteres | Rechazada, sin guardar | S01-04 |
| 20 caracteres | Se creó INC-0002 | S01-04 |
| 19 útiles + espacios externos | Rechazada | S01-06 |
| `<script>alert(1)</script>` | Guardado como texto, sin ejecutarse, visible escapado en la tabla del coordinador | S01-08 |
| Coordinador en `/incidencias/nueva` | 403 | S01-02 |
| Sin sesión | Redirige al login | S01-07 |

La consulta a SQLite mostró 3 incidencias, cada una con su evento CREAR (estado anterior
vacío, nuevo REGISTRADA), y ninguna fila para los casos rechazados.

## Intervención 2: hallazgo de codificación en `requirements.txt`
`pip freeze > requirements.txt` en PowerShell 5.1 generó el archivo en UTF-16, que `pip`
no lee en otros equipos. La IA no lo advirtió al indicar el comando. Lo detecté al revisar
los primeros bytes (`b'\xff\xfe'`), lo regeneré en UTF-8 con Python y lo verifiqué
(`b'blin'`). Archivo: `requirements.txt`, PR #11.