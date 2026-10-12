# Bitácora de IA · Antonio (fontalvomunoza-svg)

## Intervención 1: revisión de diseño (diagramas y decisión tecnológica)

| Campo | Registro |
|---|---|
| Fecha | 2026-10-11 (primer borrador) y 2026-10-12 (corrección) |
| Autor | Antonio Fontalvo (fontalvomunoza-svg) |
| Herramienta / modelo | Claude, en claude.ai. Modelo configurado en la sesión: Sonnet 5.5 (el modelo efectivo pudo variar) |
| Historia y SPEC / versión | RF01 a RF05, Parte 5 (Diseño). Basado en S01 y S02 v0.1; revisión posterior de S03, S04 y S05 v0.2 |
| Archivos | `docs/diseno/`: `1_estados`, `2_modelo_datos`, `3_secuencia_rechazo` y `4_componentes` (`.mmd` y `.png`) y `5_decision_tecnologica.md` |
| Commit / PR | `1e78223` (primer borrador), PR #9 (revisa Keyner). Commit de las correcciones: pendiente, se completa tras hacerlo |

### Objetivo y contexto
Producir los cuatro diagramas Mermaid de la Parte 5 (estados con reapertura, modelo de datos, secuencia del rechazo de solución y componentes) y una decisión tecnológica justificada, y guiar el flujo de Git y GitHub hasta abrir el Pull Request.

### Instrucción
Primera sesión (2026-10-11): chat nuevo con la guía del equipo (Word) y el enunciado (PDF) adjuntos y el mensaje «soy antonio»; después, instrucciones breves paso a paso. En esa sesión el asistente no tenía acceso al repositorio ni a `schema.sql`.
Segunda sesión (2026-10-12): mensaje con las correcciones de Juan, que comparó los diagramas con `app/schema.sql` y con el código, y la petición de ajustarlos y de indicar en qué archivo pegar y cuándo guardar.

### Respuesta relevante
- Primer borrador: diagrama de estados con las 7 transiciones de la tabla 5.1, modelo de datos, secuencia del rechazo, diagrama de componentes en tres capas y decisión tecnológica.
- Corrección: el asistente clonó el repositorio en modo lectura, leyó `schema.sql`, `db.py`, `auth.py`, `incidencias.py`, `asignaciones.py`, `reloj.py`, `prioridad.py` y `atencion.py` (rama `feature/s03-atender`) y comprobó las correcciones de Juan antes de reescribir los archivos.

### Decisión humana y justificación
- **Aceptado:** el diagrama de estados, sin cambios, porque coincide con la tabla 5.1, con `schema.sql` (CHECK de `estado`) y con las SPECS.
- **Corregido a partir de la revisión de Juan:** el modelo de datos pasa a ser idéntico a `schema.sql` (nombres de columnas, fechas `creada_en`, `asignada_en`, `registrada_en` y `creado_en`, `detalle` en lugar de `motivo`, sin `solucion_id`, acciones válidas del historial, sin columna `prioridad`, `asignaciones.incidencia_id` único). La secuencia usa la ruta `/incidencias/{id}/rechazar` y el campo `detalle`.
- **Decisión de arquitectura:** el diagrama de componentes y la decisión tecnológica describen la arquitectura **realmente implementada** (módulos que juntan ruta, regla y SQL; solo `rol_requerido`), y la separación en capas queda indicada como arquitectura objetivo. Se eligió esto en lugar de dejar un diseño que el código no cumple.
- **Descartado:** los servicios por funcionalidad, los repositorios SQL y el decorador de dueño como componentes existentes.

### Error o limitación
- El primer borrador del modelo de datos y de la secuencia usó nombres que no están en `schema.sql` (`SOLUCIONAR`, `motivo`, `solucion_id`, fechas sin los nombres reales). Lo detectó Juan al comparar con el esquema.
- El primer diagrama de componentes y la decisión tecnológica describían servicios por funcionalidad, repositorios SQL y un decorador de dueño que el código no tiene. Lo detectó Juan; se comprobó contra el código.
- Limitación de proceso: el primer borrador se hizo sin acceso al repositorio, por lo que el modelo no se pudo contrastar con el esquema antes de subirlo.

### Corrección y verificación
- Comparación de cada columna, restricción CHECK y trigger de `schema.sql` con el diagrama de datos, contra la rama `main` (commit `5ed6dda`).
- Los cuatro `.png` se regeneraron desde su `.mmd` corregido, de modo que cada imagen muestra lo mismo que su fuente. Se retiró el `.mmd` duplicado y se corrigieron los nombres `*.png.png` y `4_componentes_1.mmd`.
- Pendiente al momento de escribir esta bitácora: revisión escrita de Keyner en el PR #9 y su aprobación antes de fusionar; mi revisión escrita de S03, S04 y S05 en los PR #5, #6 y #8; confirmar el commit de correcciones.
