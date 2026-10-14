# Bitácora de IA · Sebastián

## Intervención 1 · Especificación (S03, S04 y S05)

| Campo | Valor |
|---|---|
| Fecha | 2026-10-11 y 2026-10-12 |
| Autor | Sebastián |
| Herramienta / modelo | Claude (claude.ai), Sonnet 5.5 |
| Historia y SPEC / versión | S03, S04 y S05 · de v0.1 a v0.4 |

## Objetivo y contexto

Redactar las SPECS S03 (atender), S04 (validar) y S05 (consultar e historizar) con el mismo formato que S01, a partir del enunciado del examen y de la guía del equipo.

## Prompt o instrucción

1. "Soy Sebastián, mi tarea es redactar S03, S04 y S05. Guíame paso a paso según esta guía." Se adjuntaron la guía del equipo y el enunciado, y después el texto de S01 y S02 para copiar el formato.
2. Tras la revisión de Antonio y las correcciones de Juan: se pegaron sus comentarios (identificador `incidencia_id`, nombres de acción del esquema, redondeo del porcentaje, campos de revisión) y se pidió ajustar las tres SPECS.

## Respuesta relevante

La IA entregó las tres SPECS con historia, alcance, entradas, permisos, reglas, errores, criterios Dado / Cuando / Entonces, tareas vinculadas y pruebas. Después las ajustó a v0.2 (identificador `incidencia_id`) y a v0.4 (acciones del esquema, redondeo half-up, orden de validaciones y observaciones de Antonio).

## Decisión humana y justificación

- Subí cada SPEC en su propio PR (#5, #6 y #8) para que Antonio las revisara antes de que Keyner programara.
- Dejé la revisión como pendiente en cada SPEC, porque en GitHub consta una revisión escrita de Antonio con observaciones, pero no una aprobación.
- Los PR #5 y #6 se fusionaron con las observaciones de Antonio sin atender, para desbloquear a Keyner. Las observaciones se atendieron después en la v0.4, en un PR nuevo.
- Adopté el identificador `incidencia_id` cuando Juan lo decidió.
- Al resolver el conflicto de S05 conservé la versión de `main`, porque ya incluía los cambios de `incidencia_id`.
- No modifiqué el contenido propuesto por la IA antes de subirlo; los cambios posteriores fueron los pedidos por Antonio y Juan.

## Error o limitación

La IA no tenía acceso al repositorio ni al esquema. Propuso nombres de acción que no coincidían con el CHECK de `app/schema.sql` (INICIAR_ATENCION, REGISTRAR_SOLUCION, CONFIRMAR_CIERRE y RECHAZAR_SOLUCION, en lugar de INICIAR, PROPONER_SOLUCION, CONFIRMAR y RECHAZAR). También dejó el redondeo del porcentaje sin definir. Juan lo señaló en su revisión.

## Corrección y verificación

- Cambié los nombres de acción a los del esquema en S03, S04 y S05; los motivos de rechazo y reapertura van en `eventos.detalle` y las soluciones en la tabla `soluciones`.
- Agregué el redondeo half-up con `Decimal` y `ROUND_HALF_UP` (AC-S05-19).
- Revisé, con ayuda de la IA, `app/schema.sql` en `main`: el CHECK de `eventos.accion`, los triggers contra UPDATE y DELETE y la tabla `soluciones`.
- Comprobé en GitHub que S03 y S04 en `main` dicen v0.2 y usan `incidencia_id`.
- Pendiente: nueva revisión de Antonio de la v0.4; no consta aprobación.

## Archivos, pull requests y pruebas

| Elemento | Referencia |
|---|---|
| Archivo S03 | specs/S03-atender.md |
| Archivo S04 | specs/S04-validar.md |
| Archivo S05 | specs/S05-consultar-historizar.md |
| Pull requests | PR #5, #6 y #8 (v0.2) y el PR de la rama feature/specs-alinear-esquema (v0.4) |
| Pruebas | No aplica a esta intervención: las pruebas automatizadas se escriben contra estas SPECS (Michell). No se ejecutó ninguna prueba. |
