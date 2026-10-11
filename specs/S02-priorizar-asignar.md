# SPEC S02 · Priorizar y asignar incidencia

| Campo | Valor |
|---|---|
| Versión | 0.1 (borrador) |
| Autor | Juan (JxAndres) |
| Revisor | Pendiente (sin revisión de otra persona todavía) |
| Fecha | 2026-10-11 |
| Requisito asociado | RF02 |

## Historia
Como **coordinador**, quiero **asignar una incidencia registrada a un técnico activo**, para **que alguien responsable la atienda según su prioridad**.

## Alcance y exclusiones
**Incluye:** cálculo automático de prioridad, asignación por el coordinador, transición REGISTRADA → ASIGNADA y evento en el historial.
**Excluye:** reasignación de una incidencia ya ASIGNADA, especialidad del técnico, edición de la incidencia, notificaciones.

## Entradas
| Campo | Tipo | Obligatorio | Límites / valores permitidos |
|---|---|---|---|
| incidencia_id | entero | Sí | Debe existir |
| tecnico_id | entero | Sí | Debe ser un usuario con rol TECNICO y activo |

## Precondiciones y permisos
- Usuario autenticado con rol COORDINADOR. Identidad y rol salen de la sesión.
- La incidencia debe estar en estado REGISTRADA.
- Solicitante y técnico no pueden asignar.

## Reglas y proceso
1. **Prioridad** (la calcula el servidor, el cliente no la envía):
   - riesgo_personas = true → CRITICA
   - riesgo_personas = false e impacto = ALTO → ALTA
   - riesgo_personas = false e impacto = BAJO → NORMAL
2. El servidor verifica sesión y rol COORDINADOR.
3. Verifica que la incidencia exista y esté REGISTRADA.
4. Verifica que el técnico exista, tenga rol TECNICO y esté activo.
5. En **una sola transacción** guarda la asignación, cambia el estado a ASIGNADA y crea el evento.

## Salidas y cambios persistidos
- Asignación: incidencia, técnico, coordinador que asignó, fecha UTC.
- Estado de la incidencia: ASIGNADA.
- Evento: acción ASIGNAR, autor (coordinador), fecha, estado anterior REGISTRADA, estado nuevo ASIGNADA.

## Errores y efectos que deben evitarse
- Incidencia no REGISTRADA (ya asignada o en otro estado): se rechaza (409); sin cambios.
- Técnico inexistente, inactivo o con otro rol: se rechaza (400/422); sin cambios.
- Rol no permitido: se rechaza (403); sin efectos.
- Incidencia inexistente: se rechaza (404).
- No se puede reasignar ni asignar dos veces la misma incidencia.
- Un fallo a mitad de la operación no deja asignación sin evento ni estado sin asignación.

## Criterios de aceptación
- **AC-S02-01 (prioridad CRITICA):** Dada una incidencia con riesgo_personas = true, cuando se consulta o asigna, entonces su prioridad es CRITICA, sin importar el impacto.
- **AC-S02-02 (prioridad ALTA):** Dada una incidencia con riesgo false e impacto ALTO, entonces su prioridad es ALTA.
- **AC-S02-03 (prioridad NORMAL):** Dada una incidencia con riesgo false e impacto BAJO, entonces su prioridad es NORMAL.
- **AC-S02-04 (asignación correcta):** Dado un coordinador y una incidencia REGISTRADA, cuando asigna a un técnico activo, entonces la incidencia pasa a ASIGNADA, queda guardado el técnico y se crea un evento ASIGNAR.
- **AC-S02-05 (permisos):** Dado un solicitante o un técnico, cuando intenta asignar, entonces se rechaza con 403 y no cambia nada.
- **AC-S02-06 (asignación repetida):** Dada una incidencia ya ASIGNADA, cuando el coordinador intenta asignarla de nuevo (al mismo u otro técnico), entonces se rechaza con 409 y se conservan el técnico original, el estado y el historial.
- **AC-S02-07 (técnico inválido):** Dado un coordinador, cuando asigna a un usuario inexistente, inactivo o que no es técnico, entonces se rechaza y la incidencia sigue REGISTRADA.
- **AC-S02-08 (estado incompatible):** Dada una incidencia en estado distinto de REGISTRADA (EN_ATENCION, CERRADA, etc.), cuando se intenta asignar, entonces se rechaza sin cambios.
- **AC-S02-09 (el cliente no impone prioridad):** Dado un envío que incluya un campo "prioridad", cuando se registra o asigna, entonces el servidor lo ignora y calcula la prioridad por sus reglas.
- **AC-S02-10 (atomicidad):** Dado un fallo simulado al guardar el evento, cuando se asigna, entonces no queda estado ASIGNADA ni asignación guardada.

## Diseño y tareas vinculadas
| Tarea | Cubre |
|---|---|
| T-S02-1: función pura `calcular_prioridad(riesgo, impacto)` | AC-01 a 03, 09 |
| T-S02-2: tabla `asignaciones` y campo `activo` en `usuarios` | AC-04, 07 |
| T-S02-3: ruta POST `/incidencias/<id>/asignar` con rol COORDINADOR | AC-04, 05 |
| T-S02-4: validación de estado y técnico | AC-06, 07, 08 |
| T-S02-5: transacción única asignación + estado + evento | AC-10 |

## Pruebas y resultados esperados
Se automatizan en `tests/`. Resultado esperado: todos los AC cumplen. Se completa al ejecutar.

## Decisión de revisión / versión aprobada
**Pendiente.** La revisión por otra persona no se ha realizado. Se declara como pendiente; no se registra como aprobada.