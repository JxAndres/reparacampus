# SPEC S03 · Atender incidencia

| Campo | Valor |
|---|---|
| Versión | 0.4 (borrador) |
| Autor | Sebastián |
| Revisor | Antonio (dejó revisión escrita con observaciones en el PR #5; no consta aprobación; nueva revisión de la v0.4 pendiente) |
| Fecha | 2026-10-12 |
| Requisito asociado | RF03 |

## Historia
Como **técnico asignado**, quiero **iniciar la atención de una incidencia y registrar su solución**, para **que el solicitante pueda comprobar si el problema quedó resuelto**.

## Alcance y exclusiones
**Incluye:** iniciar atención (ASIGNADA → EN_ATENCION), registrar solución (EN_ATENCION → PENDIENTE_VALIDACION), validación en servidor y eventos de historial de ambas transiciones. También aplica cuando la incidencia vuelve a EN_ATENCION tras un rechazo o una reapertura (S04): el técnico registra una nueva solución sin volver a iniciar la atención.
**Excluye:** asignación (S02), confirmación, rechazo y reapertura (S04), listados y tablero (S05), edición de una solución ya registrada, adjuntos y notificaciones.

## Entradas
| Operación | Campo | Tipo | Obligatorio | Límites / valores permitidos |
|---|---|---|---|---|
| Iniciar atención | incidencia_id (en la ruta) | entero | Sí | Id de una incidencia existente |
| Registrar solución | incidencia_id (en la ruta) | entero | Sí | Id de una incidencia existente |
| Registrar solución | solucion | texto | Sí | 20 a 800 caracteres, después de quitar espacios externos |

El cliente nunca envía autor, estado, fecha ni técnico.

El código INC-0001 es solo para mostrar en pantalla. Las rutas identifican la incidencia por su id entero (/incidencias/<int:incidencia_id>/...). Un id que no sea entero no coincide con la ruta (404).

## Precondiciones y permisos
- Usuario autenticado con rol TECNICO. El rol y la identidad salen de la sesión en el servidor.
- El técnico de la sesión debe ser el técnico asignado a esa incidencia.
- Coordinador y solicitante no pueden iniciar ni registrar soluciones.
- Iniciar atención exige estado ASIGNADA. Registrar solución exige estado EN_ATENCION.

## Reglas y proceso
**Acciones del historial.** Esta SPEC usa las acciones que acepta el esquema (`app/schema.sql`): INICIAR al iniciar la atención y PROPONER_SOLUCION al registrar una solución. Las soluciones se guardan en la tabla `soluciones`; el evento solo deja constancia de la transición.

**Orden de validaciones** (se aplica en ambas operaciones; cada paso se evalúa solo si el anterior se superó)
1. Sesión: sin sesión se redirige al login.
2. Rol: un rol distinto de TECNICO recibe 403.
3. Existencia: un id inexistente recibe 404.
4. Técnico asignado: si el técnico de la sesión no es el asignado, recibe 403.
5. Estado: si el estado no es el exigido, recibe 409.
6. Texto (solo al registrar solución): una solución fuera de 20 a 800 caracteres recibe 400/422.
Un rechazo no genera efectos ni eventos.

**Iniciar atención**
1. El servidor aplica el orden de validaciones.
2. En **una sola transacción** cambia el estado a EN_ATENCION y crea el evento INICIAR (autor, fecha UTC del servidor, estado anterior y nuevo).

**Registrar solución**
1. El servidor aplica el orden de validaciones.
2. Quita espacios externos y valida el largo (20 a 800).
3. En **una sola transacción** guarda la solución en la tabla `soluciones`, cambia el estado a PENDIENTE_VALIDACION y crea el evento PROPONER_SOLUCION.
4. Las soluciones anteriores (si hubo rechazo o reapertura) no se modifican ni se borran: cada solución nueva se agrega como un registro más.

## Salidas y cambios persistidos
- Iniciar: incidencia en EN_ATENCION, evento INICIAR.
- Registrar: nueva fila en `soluciones` (texto, autor, fecha UTC), incidencia en PENDIENTE_VALIDACION, evento PROPONER_SOLUCION.
- Respuesta de éxito con el nuevo estado.

## Errores y efectos que deben evitarse
- Sin sesión: se redirige al login; sin efectos.
- Rol incorrecto o técnico no asignado: 403; sin efectos.
- Incidencia inexistente: 404; sin efectos.
- Estado incompatible: 409; sin efectos.
- Solución fuera de 20 a 800 caracteres: 400/422; sin efectos.
- Un fallo a mitad de la operación no deja estado cambiado sin evento ni solución sin evento.
- Texto con HTML o scripts se guarda como texto y se muestra escapado.
- No se crean transiciones distintas de las dos descritas.

## Criterios de aceptación
- **AC-S03-01 (normal, iniciar):** Dado un técnico T01 autenticado y una incidencia ASIGNADA a T01, cuando inicia la atención, entonces queda EN_ATENCION, conserva a T01 y se crea un evento INICIAR con autor, fecha, estado anterior ASIGNADA y estado nuevo EN_ATENCION.
- **AC-S03-02 (normal, solución):** Dado un técnico T01 autenticado y una incidencia EN_ATENCION asignada a T01, cuando registra una solución válida de 40 caracteres, entonces se guarda la solución en `soluciones`, la incidencia queda PENDIENTE_VALIDACION y se crea un evento PROPONER_SOLUCION.
- **AC-S03-03 (permisos, técnico no asignado inicia):** Dado una incidencia ASIGNADA a T01, cuando el técnico T02 intenta iniciar la atención, entonces se rechaza con 403 y no cambian estado, soluciones ni historial.
- **AC-S03-04 (permisos, técnico no asignado registra):** Dado una incidencia EN_ATENCION asignada a T01, cuando el técnico T02 intenta registrar una solución, entonces se rechaza con 403 y no cambian estado, soluciones ni historial.
- **AC-S03-05 (permisos, otros roles inician):** Dado un coordinador o un solicitante autenticado, cuando intenta iniciar la atención de una incidencia ASIGNADA, entonces se rechaza con 403 y no cambia nada.
- **AC-S03-06 (permisos, otros roles registran):** Dado un coordinador o un solicitante autenticado, cuando intenta registrar una solución en una incidencia EN_ATENCION, entonces se rechaza con 403 y no cambia nada.
- **AC-S03-07 (estado incompatible, solución antes de iniciar):** Dado una incidencia ASIGNADA a T01, cuando T01 intenta registrar una solución sin haber iniciado la atención, entonces se rechaza con 409 y la incidencia sigue ASIGNADA sin solución nueva.
- **AC-S03-08 (estado incompatible, registrar en otros estados):** Dado una incidencia asignada a T01 en estado REGISTRADA, PENDIENTE_VALIDACION o CERRADA, cuando T01 intenta registrar una solución, entonces se rechaza con 409 y no cambian estado, soluciones ni historial.
- **AC-S03-09 (estado incompatible, iniciar):** Dado una incidencia en estado REGISTRADA, EN_ATENCION, PENDIENTE_VALIDACION o CERRADA, cuando el técnico intenta iniciar la atención, entonces se rechaza con 409 y no cambia nada.
- **AC-S03-10 (límite inferior):** Dado una incidencia EN_ATENCION asignada a T01, cuando T01 envía una solución de 19 caracteres, entonces se rechaza; con 20 caracteres, se acepta.
- **AC-S03-11 (límite superior):** Dado una incidencia EN_ATENCION asignada a T01, cuando T01 envía una solución de 800 caracteres se acepta, y con 801 se rechaza.
- **AC-S03-12 (espacios externos):** Dado una incidencia EN_ATENCION asignada a T01, cuando T01 envía una solución de 19 caracteres útiles más espacios al inicio y al final, entonces se rechaza porque el límite se aplica tras retirar espacios.
- **AC-S03-13 (incidencia inexistente):** Dado un id de incidencia inexistente, cuando un técnico autenticado intenta iniciar la atención o registrar una solución, entonces responde 404 y no cambia nada.
- **AC-S03-14 (sin sesión):** Dado un visitante sin sesión, cuando intenta iniciar la atención o registrar una solución, entonces se redirige al login y no cambia nada.
- **AC-S03-15 (seguridad de texto):** Dado una incidencia EN_ATENCION asignada a T01, cuando T01 registra una solución con `<script>alert(1)</script>` de 20 o más caracteres, entonces se guarda como texto y se muestra escapada sin ejecutarse.
- **AC-S03-16 (atomicidad):** Dado un fallo simulado al guardar el evento, cuando T01 inicia la atención o registra una solución, entonces no queda estado cambiado, ni solución guardada, ni evento parcial.
- **AC-S03-17 (nueva solución tras rechazo):** Dado una incidencia que el solicitante rechazó y volvió a EN_ATENCION con el técnico T01 y una solución anterior, cuando T01 registra una nueva solución válida, entonces queda PENDIENTE_VALIDACION con una solución nueva en `soluciones`, la solución anterior se conserva intacta, el técnico sigue siendo T01 y se crea un evento PROPONER_SOLUCION.
- **AC-S03-18 (nueva solución tras reapertura):** Dado una incidencia reabierta que volvió a EN_ATENCION con el técnico T01, un cierre anterior y una solución anterior, cuando T01 registra una nueva solución válida, entonces queda PENDIENTE_VALIDACION, se conservan el cierre y la solución anteriores, y se crea un evento PROPONER_SOLUCION.
- **AC-S03-19 (orden de validaciones):** Dado un técnico T02 no asignado a una incidencia ASIGNADA, cuando intenta registrar una solución de 5 caracteres, entonces responde 403 (no 409 ni 400/422); y dado el técnico asignado T01 con la incidencia ASIGNADA, cuando registra una solución de 5 caracteres, entonces responde 409 (no 400/422); y dado un visitante sin sesión que pide un id inexistente, entonces se redirige al login (no 404). En los tres casos sin efectos.

## Diseño y tareas vinculadas
| Tarea | Cubre |
|---|---|
| T-S03-1: tabla `soluciones` (varias por incidencia) en el esquema SQL | AC-02, 16, 17, 18 |
| T-S03-2: ruta POST de iniciar atención por `incidencia_id` con control de técnico asignado y estado | AC-01, 03, 05, 09, 13, 14 |
| T-S03-3: ruta POST de registrar solución por `incidencia_id` con validación de largo | AC-02, 04, 06, 07, 08, 10, 11, 12 |
| T-S03-4: decorador de rol, sesión y verificación del técnico asignado | AC-03, 04, 05, 06, 14 |
| T-S03-5: plantilla Jinja con escape automático | AC-15 |
| T-S03-6: transacción única estado + solución + evento (acciones INICIAR y PROPONER_SOLUCION) | AC-16 |
| T-S03-7: orden de validaciones (sesión, rol, existencia, técnico asignado, estado, texto) | AC-13, 14, 19 |
| T-S03-8: registro de nuevas soluciones tras rechazo o reapertura sin borrar las anteriores | AC-17, 18 |

## Pruebas y resultados esperados
Se automatizan en `tests/`: iniciar y registrar con técnico asignado, técnico no asignado, otros roles, estados incompatibles, límites de 19/20 y 800/801, espacios externos, id inexistente, sin sesión, texto con scripts, atomicidad, nueva solución tras rechazo y tras reapertura, y orden de validaciones. Resultado esperado: todos los AC cumplen. Se completa al ejecutar; si algo no se ejecuta, se declara pendiente.

## Decisión de revisión / versión aprobada
**Pendiente.** Antonio dejó una revisión escrita con observaciones en el PR #5, atendidas en esta versión (v0.4); no consta una aprobación. La nueva revisión por otra persona no se ha realizado. No se registra como aprobada.