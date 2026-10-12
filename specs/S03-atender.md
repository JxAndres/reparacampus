# SPEC S03 · Atender incidencia

| Campo | Valor |
|---|---|
| Versión | 0.2 (borrador) |
| Autor | Sebastián |
| Revisor | Antonio (pendiente) |
| Fecha | 2026-10-11 |
| Requisito asociado | RF03 |

## Historia
Como **técnico asignado**, quiero **iniciar la atención de una incidencia y registrar su solución**, para **que el solicitante pueda comprobar si el problema quedó resuelto**.

## Alcance y exclusiones
**Incluye:** iniciar atención (ASIGNADA → EN_ATENCION), registrar solución (EN_ATENCION → PENDIENTE_VALIDACION), validación en servidor y eventos de historial de ambas transiciones.
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
**Iniciar atención**
1. El servidor verifica sesión, rol y que el técnico sea el asignado.
2. Verifica que el estado sea ASIGNADA.
3. En **una sola transacción** cambia el estado a EN_ATENCION y crea el evento INICIAR_ATENCION (autor, fecha UTC del servidor, estado anterior y nuevo).

**Registrar solución**
1. El servidor verifica sesión, rol y que el técnico sea el asignado.
2. Verifica que el estado sea EN_ATENCION.
3. Quita espacios externos y valida el largo (20 a 800).
4. En **una sola transacción** guarda la solución, cambia el estado a PENDIENTE_VALIDACION y crea el evento REGISTRAR_SOLUCION.
5. Las soluciones anteriores (si hubo rechazo o reapertura) no se modifican ni se borran.

## Salidas y cambios persistidos
- Iniciar: incidencia en EN_ATENCION, evento INICIAR_ATENCION.
- Registrar: nueva solución (texto, autor, fecha UTC), incidencia en PENDIENTE_VALIDACION, evento REGISTRAR_SOLUCION.
- Respuesta de éxito con el nuevo estado.

## Errores y efectos que deben evitarse
- Sin sesión: se redirige al login; sin efectos.
- Rol o técnico incorrecto: 403; sin efectos.
- Incidencia inexistente: 404; sin efectos.
- Estado incompatible: 409; sin efectos.
- Solución fuera de 20 a 800 caracteres: 400/422; sin efectos.
- Un fallo a mitad de la operación no deja estado cambiado sin evento ni solución sin evento.
- Texto con HTML o scripts se guarda como texto y se muestra escapado.
- No se crean transiciones distintas de las dos descritas.

## Criterios de aceptación
- **AC-S03-01 (normal, iniciar):** Dado un técnico T01 autenticado y una incidencia ASIGNADA a T01, cuando inicia la atención, entonces queda EN_ATENCION, conserva a T01 y se crea un evento INICIAR_ATENCION con autor, fecha, estado anterior ASIGNADA y estado nuevo EN_ATENCION.
- **AC-S03-02 (normal, solución):** Dado un técnico T01 autenticado y una incidencia EN_ATENCION asignada a T01, cuando registra una solución válida de 40 caracteres, entonces se guarda la solución, la incidencia queda PENDIENTE_VALIDACION y se crea un evento REGISTRAR_SOLUCION.
- **AC-S03-03 (permisos, técnico no asignado):** Dado una incidencia ASIGNADA a T01, cuando el técnico T02 intenta iniciar la atención o registrar una solución, entonces se rechaza con 403 y no cambian estado, soluciones ni historial.
- **AC-S03-04 (permisos, otros roles):** Dado un coordinador o un solicitante autenticado, cuando intenta iniciar atención o registrar una solución, entonces se rechaza con 403 y no cambia nada.
- **AC-S03-05 (estado incompatible, solución antes de iniciar):** Dado una incidencia ASIGNADA a T01, cuando T01 intenta registrar una solución sin haber iniciado la atención, entonces se rechaza con 409 y la incidencia sigue ASIGNADA sin solución nueva.
- **AC-S03-06 (estado incompatible, iniciar):** Dado una incidencia en estado REGISTRADA, EN_ATENCION, PENDIENTE_VALIDACION o CERRADA, cuando el técnico intenta iniciar la atención, entonces se rechaza con 409 y no cambia nada.
- **AC-S03-07 (límite inferior):** Dado una incidencia EN_ATENCION asignada a T01, cuando T01 envía una solución de 19 caracteres, entonces se rechaza; con 20 caracteres, se acepta.
- **AC-S03-08 (límite superior):** Dado una incidencia EN_ATENCION asignada a T01, cuando T01 envía una solución de 800 caracteres se acepta, y con 801 se rechaza.
- **AC-S03-09 (espacios externos):** Dado una incidencia EN_ATENCION asignada a T01, cuando T01 envía una solución de 19 caracteres útiles más espacios al inicio y al final, entonces se rechaza porque el límite se aplica tras retirar espacios.
- **AC-S03-10 (incidencia inexistente y sin sesión):** Dado un id de incidencia inexistente, cuando un técnico autenticado intenta operar, entonces responde 404; y dado un visitante sin sesión, cuando intenta operar, entonces se redirige al login. En ambos casos sin efectos.
- **AC-S03-11 (seguridad de texto):** Dado una incidencia EN_ATENCION asignada a T01, cuando T01 registra una solución con `<script>alert(1)</script>` de 20 o más caracteres, entonces se guarda como texto y se muestra escapada sin ejecutarse.
- **AC-S03-12 (atomicidad):** Dado un fallo simulado al guardar el evento, cuando T01 registra una solución, entonces no queda estado cambiado, ni solución guardada, ni evento parcial.

## Diseño y tareas vinculadas
| Tarea | Cubre |
|---|---|
| T-S03-1: tabla `soluciones` (varias