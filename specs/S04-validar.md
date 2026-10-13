# SPEC S04 · Validar solución (confirmar, rechazar y reabrir)

| Campo | Valor |
|---|---|
| Versión | 0.4 (borrador) |
| Autor | Sebastián |
| Revisor | Antonio (pendiente; no consta aprobación en GitHub) |
| Fecha | 2026-10-12 |
| Requisito asociado | RF04 |

## Historia
Como **solicitante dueño de una incidencia**, quiero **confirmar, rechazar o reabrir la solución registrada**, para **asegurarme de que el problema quedó realmente resuelto**.

## Alcance y exclusiones
**Incluye:** confirmar (PENDIENTE_VALIDACION → CERRADA), rechazar con motivo (PENDIENTE_VALIDACION → EN_ATENCION), reabrir con motivo dentro de 48 horas (CERRADA → EN_ATENCION), validación en servidor y eventos de historial de cada transición.
**Excluye:** atención y registro de solución (S03), asignación (S02), listados e historial consultable (S05), cierre automático, edición de reportes, reasignación de técnico, adjuntos y notificaciones.

## Entradas
| Operación | Campo | Tipo | Obligatorio | Límites / valores permitidos |
|---|---|---|---|---|
| Confirmar | incidencia_id (en la ruta) | entero | Sí | Id de una incidencia existente |
| Rechazar | incidencia_id (en la ruta) | entero | Sí | Id de una incidencia existente |
| Rechazar | motivo | texto | Sí | 10 a 300 caracteres, después de quitar espacios externos |
| Reabrir | incidencia_id (en la ruta) | entero | Sí | Id de una incidencia existente |
| Reabrir | motivo | texto | Sí | 10 a 300 caracteres, después de quitar espacios externos |

El cliente nunca envía autor, estado, fecha ni técnico. La hora la obtiene el servidor.

El código INC-0001 es solo para mostrar en pantalla. Las rutas identifican la incidencia por su id entero (/incidencias/<int:incidencia_id>/...). Un id que no sea entero no coincide con la ruta (404).

## Precondiciones y permisos
- Usuario autenticado con rol SOLICITANTE y que sea el **dueño** (autor) de la incidencia. Rol e identidad salen de la sesión en el servidor.
- El coordinador y el técnico no pueden confirmar, rechazar ni reabrir en nombre del solicitante.
- Confirmar y rechazar exigen estado PENDIENTE_VALIDACION. Reabrir exige estado CERRADA.

## Reglas y proceso
**Acciones del historial.** Esta SPEC usa las acciones que acepta el esquema (`app/schema.sql`): CONFIRMAR, RECHAZAR y REABRIR. El motivo de un rechazo o de una reapertura se guarda en `eventos.detalle`. Las soluciones viven en la tabla `soluciones` y nunca se modifican.

**Orden de validaciones** (se aplica en las tres operaciones; cada paso se evalúa solo si el anterior se superó)
1. Sesión: sin sesión se redirige al login.
2. Rol: un rol distinto de SOLICITANTE recibe 403.
3. Existencia: un id inexistente recibe 404.
4. Dueño: si el solicitante de la sesión no es el dueño, recibe 403.
5. Estado: si el estado no es el exigido, recibe 409.
6. Motivo (rechazar y reabrir): un motivo fuera de 10 a 300 caracteres recibe 400/422.
7. Plazo (solo reabrir): si pasaron más de 48 horas desde el último cierre, recibe 409.
Un rechazo no genera efectos ni eventos.

**Confirmar**
1. El servidor aplica el orden de validaciones.
2. En **una sola transacción** cambia el estado a CERRADA y crea el evento CONFIRMAR con la fecha UTC del servidor, que queda como fecha del cierre.

**Rechazar**
1. El servidor aplica el orden de validaciones y quita espacios externos al motivo.
2. En **una sola transacción** cambia el estado a EN_ATENCION, conserva el mismo técnico y la solución anterior, y crea el evento RECHAZAR con el motivo en `detalle`.

**Reabrir**
1. El servidor aplica el orden de validaciones y quita espacios externos al motivo.
2. Calcula el tiempo transcurrido desde el **último cierre** (el evento CONFIRMAR más reciente) con la hora UTC del servidor. Si es **menor o igual a 48 horas**, procede; si es mayor, rechaza.
3. En **una sola transacción** cambia el estado a EN_ATENCION, conserva el mismo técnico y crea el evento REABRIR con el motivo en `detalle`.

**Reglas comunes**
- Se conservan todas las soluciones y todos los cierres anteriores; nada se edita ni se borra.
- Si tras reabrir se vuelve a cerrar, el plazo de 48 horas se cuenta desde ese nuevo cierre.
- La hora actual se obtiene de una función inyectable (`reloj.ahora()`), para poder probar el límite sin esperar ni cambiar el reloj del sistema.

## Salidas y cambios persistidos
- Confirmar: incidencia CERRADA, evento CONFIRMAR con la fecha del cierre.
- Rechazar: incidencia EN_ATENCION, mismo técnico, solución anterior intacta, evento RECHAZAR con el motivo en `detalle`.
- Reabrir: incidencia EN_ATENCION, mismo técnico, cierres y soluciones anteriores intactos, evento REABRIR con el motivo en `detalle`.
- Respuesta de éxito con el nuevo estado.

## Errores y efectos que deben evitarse
- Sin sesión: se redirige al login; sin efectos.
- Rol o dueño incorrecto: 403; sin efectos.
- Incidencia inexistente: 404; sin efectos.
- Estado incompatible o plazo de 48 horas vencido: 409; sin efectos.
- Motivo fuera de 10 a 300 caracteres: 400/422; sin efectos.
- Un fallo a mitad de la operación no deja estado cambiado sin evento ni evento sin cambio de estado.
- El navegador no puede elegir la hora efectiva.
- Texto con HTML o scripts se guarda como texto y se muestra escapado.
- No se crean transiciones distintas de las tres descritas.

## Criterios de aceptación
- **AC-S04-01 (normal, confirmar):** Dado un reporte propio PENDIENTE_VALIDACION con técnico T01 y solución registrada, cuando el solicitante dueño lo confirma, entonces queda CERRADA y se crea un evento CONFIRMAR con autor, fecha UTC del cierre, estado anterior y estado nuevo.
- **AC-S04-02 (normal, rechazar):** Dado un reporte propio PENDIENTE_VALIDACION con técnico T01 y solución registrada, cuando el solicitante lo rechaza con "El daño sigue presente", entonces queda EN_ATENCION, conserva a T01 y la solución anterior, y se crea un evento RECHAZAR que registra quién rechazó, cuándo y el motivo en `detalle`.
- **AC-S04-03 (normal, reabrir):** Dado un reporte propio CERRADA hace 47 horas con técnico T01, cuando el solicitante lo reabre con el motivo "El daño volvió a aparecer", entonces queda EN_ATENCION, conserva a T01, conserva el cierre y la solución anteriores, y se crea un evento REABRIR con el motivo en `detalle`.
- **AC-S04-04 (permisos, confirmar y rechazar):** Dado un reporte PENDIENTE_VALIDACION de un solicitante A, cuando otro solicitante B, el coordinador o un técnico intenta confirmarlo o rechazarlo, entonces se rechaza con 403 y no cambian estado, soluciones ni historial.
- **AC-S04-05 (permisos, reabrir):** Dado un reporte CERRADA de un solicitante A dentro de las 48 horas, cuando otro solicitante B, el coordinador o un técnico intenta reabrirlo, entonces se rechaza con 403 y no cambia nada.
- **AC-S04-06 (estado incompatible, confirmar y rechazar):** Dado un reporte propio en estado REGISTRADA, ASIGNADA, EN_ATENCION o CERRADA, cuando el solicitante intenta confirmarlo o rechazarlo, entonces se rechaza con 409 y no cambia nada.
- **AC-S04-07 (estado incompatible, reabrir):** Dado un reporte propio en estado distinto de CERRADA, cuando el solicitante intenta reabrirlo, entonces se rechaza con 409 y no cambia nada.
- **AC-S04-08 (límite inferior del motivo):** Dado un reporte propio PENDIENTE_VALIDACION (o CERRADA dentro del plazo), cuando el solicitante envía un motivo de 9 caracteres para rechazar o reabrir, entonces se rechaza; con 10 caracteres, se acepta.
- **AC-S04-09 (límite superior del motivo):** Dado un reporte propio PENDIENTE_VALIDACION (o CERRADA dentro del plazo), cuando el solicitante envía un motivo de 300 caracteres, entonces se acepta; con 301, se rechaza.
- **AC-S04-10 (espacios externos):** Dado un reporte propio PENDIENTE_VALIDACION, cuando el solicitante envía un motivo de 9 caracteres útiles más espacios al inicio y al final, entonces se rechaza porque el límite se aplica tras retirar espacios.
- **AC-S04-11 (límite exacto de 48 horas):** Dado un reporte propio cerrado exactamente 48 horas antes de la hora del servidor, cuando el solicitante lo reabre con un motivo válido, entonces se acepta y queda EN_ATENCION.
- **AC-S04-12 (fuera de plazo):** Dado un reporte propio cerrado 48 horas y 1 segundo antes de la hora del servidor, cuando el solicitante intenta reabrirlo, entonces se rechaza con 409 y no cambian estado, cierres ni historial.
- **AC-S04-13 (conservación del historial):** Dado un reporte que pasó por solución, rechazo, nueva solución, cierre y reapertura, cuando se consulta su historial, entonces conserva todas las soluciones, todos los cierres, los motivos y los eventos (INICIAR, PROPONER_SOLUCION, RECHAZAR, PROPONER_SOLUCION, CONFIRMAR, REABRIR), sin edición ni borrado, y con el mismo técnico.
- **AC-S04-14 (plazo desde el último cierre):** Dado un reporte cerrado, reabierto y cerrado de nuevo, cuando el solicitante intenta reabrirlo, entonces el plazo de 48 horas se cuenta desde el último cierre y no desde el primero.
- **AC-S04-15 (hora del servidor):** Dado un solicitante que envía un campo de fecha u hora en la petición, cuando confirma, rechaza o reabre, entonces el servidor ignora ese dato y usa su propia hora UTC.
- **AC-S04-16 (inexistente y sin sesión):** Dado un id de incidencia inexistente, cuando un solicitante autenticado opera, entonces responde 404; y dado un visitante sin sesión, cuando intenta operar, entonces se redirige al login. En ambos casos sin efectos.
- **AC-S04-17 (seguridad de texto):** Dado un reporte propio PENDIENTE_VALIDACION, cuando el solicitante rechaza con un motivo `<script>alert(1)</script>`, entonces se guarda como texto y se muestra escapado sin ejecutarse.
- **AC-S04-18 (atomicidad):** Dado un fallo simulado al guardar el evento, cuando el solicitante confirma, rechaza o reabre, entonces no queda estado cambiado ni evento parcial.
- **AC-S04-19 (orden de validaciones):** Dado un solicitante B que no es el dueño de un reporte ASIGNADO, cuando intenta rechazarlo con un motivo de 3 caracteres, entonces responde 403 (no 409 ni 400/422); y dado el dueño con el reporte ASIGNADO, cuando lo rechaza con un motivo de 3 caracteres, entonces responde 409 (no 400/422); y dado el dueño de un reporte CERRADA hace más de 48 horas, cuando lo reabre con un motivo de 3 caracteres, entonces responde 400/422 (no 409 de plazo). En los tres casos sin efectos.

## Diseño y tareas vinculadas
| Tarea | Cubre |
|---|---|
| T-S04-1: acciones CONFIRMAR, RECHAZAR y REABRIR en el esquema; motivo en `eventos.detalle` | AC-01, 02, 03, 13, 14 |
| T-S04-2: ruta POST de confirmar por `incidencia_id` con control de dueño y estado | AC-01, 04, 06, 16 |
| T-S04-3: ruta POST de rechazar con validación de motivo | AC-02, 04, 06, 08, 09, 10 |
| T-S04-4: ruta POST de reabrir con validación de motivo y plazo desde el último CONFIRMAR | AC-03, 05, 07, 08, 09, 11, 12, 14 |
| T-S04-5: función de reloj inyectable (hora UTC del servidor) | AC-11, 12, 15 |
| T-S04-6: decorador de rol, sesión y verificación del dueño | AC-04, 05, 16 |
| T-S04-7: plantilla Jinja con escape automático | AC-17 |
| T-S04-8: transacción única estado + evento | AC-18 |
| T-S04-9: orden de validaciones (sesión, rol, existencia, dueño, estado, motivo, plazo) | AC-16, 19 |

## Pruebas y resultados esperados
Se automatizan en `tests/`, con tres pruebas de integración: flujo de cierre, rechazo con nueva solución, y cierre → reapertura → nueva solución → nuevo cierre. El límite de 48 horas se prueba con reloj controlado. Resultado esperado: todos los AC cumplen. Se completa al ejecutar; si algo no se ejecuta, se declara pendiente.

## Decisión de revisión / versión aprobada
**Pendiente.** No consta una aprobación de otra persona en GitHub. La revisión previa a la implementación no se ha realizado. No se registra como aprobada.