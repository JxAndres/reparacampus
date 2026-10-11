# SPEC S04 · Validar solución (confirmar, rechazar y reabrir)

| Campo | Valor |
|---|---|
| Versión | 0.1 (borrador) |
| Autor | Sebastián |
| Revisor | Antonio (pendiente) |
| Fecha | 2026-10-11 |
| Requisito asociado | RF04 |

## Historia
Como **solicitante dueño de una incidencia**, quiero **confirmar, rechazar o reabrir la solución registrada**, para **asegurarme de que el problema quedó realmente resuelto**.

## Alcance y exclusiones
**Incluye:** confirmar (PENDIENTE_VALIDACION → CERRADA), rechazar con motivo (PENDIENTE_VALIDACION → EN_ATENCION), reabrir con motivo dentro de 48 horas (CERRADA → EN_ATENCION), validación en servidor y eventos de historial de cada transición.
**Excluye:** atención y registro de solución (S03), asignación (S02), listados e historial consultable (S05), cierre automático, edición de reportes, reasignación de técnico, adjuntos y notificaciones.

## Entradas
| Operación | Campo | Tipo | Obligatorio | Límites / valores permitidos |
|---|---|---|---|---|
| Confirmar | codigo (en la ruta) | texto | Sí | Código de una incidencia existente |
| Rechazar | codigo (en la ruta) | texto | Sí | Código de una incidencia existente |
| Rechazar | motivo | texto | Sí | 10 a 300 caracteres, después de quitar espacios externos |
| Reabrir | codigo (en la ruta) | texto | Sí | Código de una incidencia existente |
| Reabrir | motivo | texto | Sí | 10 a 300 caracteres, después de quitar espacios externos |

El cliente nunca envía autor, estado, fecha ni técnico. La hora la obtiene el servidor.

## Precondiciones y permisos
- Usuario autenticado con rol SOLICITANTE y que sea el **dueño** (autor) de la incidencia. Rol e identidad salen de la sesión en el servidor.
- El coordinador y el técnico no pueden confirmar, rechazar ni reabrir en nombre del solicitante.
- Confirmar y rechazar exigen estado PENDIENTE_VALIDACION. Reabrir exige estado CERRADA.

## Reglas y proceso
**Confirmar**
1. El servidor verifica sesión, rol y que el usuario sea el dueño.
2. Verifica que el estado sea PENDIENTE_VALIDACION.
3. En **una sola transacción** cambia el estado a CERRADA, registra la fecha UTC del cierre y crea el evento CONFIRMAR_CIERRE.

**Rechazar**
1. El servidor verifica sesión, rol, dueño y estado PENDIENTE_VALIDACION.
2. Quita espacios externos al motivo y valida su largo (10 a 300).
3. En **una sola transacción** cambia el estado a EN_ATENCION, conserva el mismo técnico y la solución anterior, y crea el evento RECHAZAR_SOLUCION con el motivo.

**Reabrir**
1. El servidor verifica sesión, rol, dueño y estado CERRADA.
2. Quita espacios externos al motivo y valida su largo (10 a 300).
3. Calcula el tiempo transcurrido desde el **último cierre** con la hora UTC del servidor. Si es **menor o igual a 48 horas**, procede; si es mayor, rechaza.
4. En **una sola transacción** cambia el estado a EN_ATENCION, conserva el mismo técnico, y crea el evento REABRIR con el motivo.

**Reglas comunes**
- Se conservan todas las soluciones y todos los cierres anteriores; nada se edita ni se borra.
- Si tras reabrir se vuelve a cerrar, el plazo de 48 horas se cuenta desde ese nuevo cierre.
- La hora actual se obtiene de una función inyectable, para poder probar el límite sin esperar ni cambiar el reloj del sistema.

## Salidas y cambios persistidos
- Confirmar: incidencia CERRADA, nuevo cierre con fecha UTC, evento CONFIRMAR_CIERRE.
- Rechazar: incidencia EN_ATENCION, mismo técnico, solución anterior intacta, evento RECHAZAR_SOLUCION con motivo.
- Reabrir: incidencia EN_ATENCION, mismo técnico, cierres y soluciones anteriores intactos, evento REABRIR con motivo.
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
- **AC-S04-01 (normal, confirmar):** Dado un reporte propio PENDIENTE_VALIDACION con técnico T01 y solución registrada, cuando el solicitante dueño lo confirma, entonces queda CERRADA, se guarda la fecha UTC del cierre y se crea un evento CONFIRMAR_CIERRE con autor, fecha, estado anterior y estado nuevo.
- **AC-S04-02 (normal, rechazar):** Dado un reporte propio PENDIENTE_VALIDACION con técnico T01 y solución registrada, cuando el solicitante lo rechaza con "El daño sigue presente", entonces queda EN_ATENCION, conserva a T01 y la solución anterior, y registra quién rechazó, cuándo y por qué.
- **AC-S04-03 (normal, reabrir):** Dado un reporte propio CERRADA hace 47 horas con técnico T01, cuando el solicitante lo reabre con el motivo "El daño volvió a aparecer", entonces queda EN_ATENCION, conserva a T01, conserva el cierre y la solución anteriores, y se crea un evento REABRIR con el motivo.
- **AC-S04-04 (permisos, confirmar y rechazar):** Dado un reporte PENDIENTE_VALIDACION de un solicitante A, cuando otro solicitante B, el coordinador o un técnico intenta confirmarlo o rechazarlo, entonces se rechaza con 403 y no cambian estado, soluciones ni historial.
- **AC-S04-05 (permisos, reabrir):** Dado un reporte CERRADA de un solicitante A dentro de las 48 horas, cuando otro solicitante B, el coordinador o un técnico intenta reabrirlo, entonces se rechaza con 403 y no cambia nada.
- **AC-S04-06 (estado incompatible, confirmar y rechazar):** Dado un reporte propio en estado REGISTRADA, ASIGNADA, EN_ATENCION o CERRADA, cuando el solicitante intenta confirmarlo o rechazarlo, entonces se rechaza con 409 y no cambia nada.
- **AC-S04-07 (estado incompatible, reabrir):** Dado un reporte propio en estado distinto de CERRADA, cuando el solicitante intenta reabrirlo, entonces se rechaza con 409 y no cambia nada.
- **AC-S04-08 (límite inferior del motivo):** Dado un reporte propio PENDIENTE_VALIDACION (o CERRADA dentro del plazo), cuando el solicitante envía un motivo de 9 caracteres para rechazar o reabrir, entonces se rechaza; con 10 caracteres, se acepta.
- **AC-S04-09 (límite superior del motivo):** Dado un reporte propio PENDIENTE_VALIDACION (o CERRADA dentro del plazo), cuando el solicitante envía un motivo de 300 caracteres, entonces se acepta; con 301, se rechaza.
- **AC-S04-10 (espacios externos):** Dado un reporte propio PENDIENTE_VALIDACION, cuando el solicitante envía un motivo de 9 caracteres útiles más espacios al inicio y al final, entonces se rechaza porque el límite se aplica tras retirar espacios.
- **AC-S04-11 (límite exacto de 48 horas):** Dado un reporte propio cerrado exactamente 48 horas antes de la hora del servidor, cuando el solicitante lo reabre con un motivo válido, entonces se acepta y queda EN_ATENCION.
- **AC-S04-12 (fuera de plazo):** Dado un reporte propio cerrado 48 horas y 1 segundo antes de la hora del servidor, cuando el solicitante intenta reabrirlo, entonces se rechaza con 409 y no cambian estado, cierres ni historial.
- **AC-S04-13 (conservación del historial):** Dado un reporte que pasó por solución, rechazo, nueva solución, cierre y reapertura, cuando se consulta su historial, entonces conserva todas las soluciones, todos los cierres, los motivos y los eventos, sin edición ni borrado, y con el mismo técnico.
- **AC-S04-14 (plazo desde el último cierre):** Dado un reporte cerrado, reabierto y cerrado de nuevo, cuando el solicitante intenta reabrirlo, entonces el plazo de 48 horas se cuenta desde el último cierre y no desde el primero.
- **AC-S04-15 (hora del servidor):** Dado un solicitante que envía un campo de fecha u hora en la petición, cuando confirma, rechaza o reabre, entonces el servidor ignora ese dato y usa su propia hora UTC.
- **AC-S04-16 (inexistente y sin sesión):** Dado un código inexistente, cuando un solicitante autenticado opera, entonces responde 404; y dado un visitante sin sesión, cuando intenta operar, entonces se redirige al login. En ambos casos sin efectos.
- **AC-S04-17 (seguridad de texto):** Dado un reporte propio PENDIENTE_VALIDACION, cuando el solicitante rechaza con un motivo `<script>alert(1)</script>`, entonces se guarda como texto y se muestra escapado sin ejecutarse.
- **AC-S04-18 (atomicidad):** Dado un fallo simulado al guardar el evento, cuando el solicitante confirma, rechaza o reabre, entonces no queda estado cambiado ni evento parcial.

## Diseño y tareas vinculadas
| Tarea | Cubre |
|---|---|
| T-S04-1: tabla `cierres` (uno por cada confirmación) y columna de motivo en `eventos` | AC-01, 03, 13, 14 |
| T-S04-2: ruta POST de confirmar con control de dueño y estado | AC-01, 04, 06, 16 |
| T-S04-3: ruta POST de rechazar con validación de motivo | AC-02, 04, 06, 08, 09, 10 |
| T-S04-4: ruta POST de reabrir con validación de motivo y plazo | AC-03, 05, 07, 08, 09, 11, 12, 14 |
| T-S04-5: función de reloj inyectable (hora UTC del servidor) | AC-11, 12, 15 |
| T-S04-6: decorador de rol, sesión y verificación del dueño | AC-04, 05, 16 |
| T-S04-7: plantilla Jinja con escape automático | AC-17 |
| T-S04-8: transacción única estado + cierre + evento | AC-18 |

## Pruebas y resultados esperados
Se automatizan en `tests/`, con tres pruebas de integración: flujo de cierre, rechazo con nueva solución, y cierre → reapertura → nueva solución → nuevo cierre. El límite de 48 horas se prueba con reloj controlado. Resultado esperado: todos los AC cumplen. Se completa al ejecutar; si algo no se ejecuta, se declara pendiente.

## Decisión de revisión / versión aprobada
**Pendiente.** La revisión por otra persona no se ha realizado. No se registra como aprobada. 