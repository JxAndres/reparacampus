# SPEC S05 · Consultar e historizar

| Campo | Valor |
|---|---|
| Versión | 0.2 (borrador) |
| Autor | Sebastián |
| Revisor | Antonio (pendiente) |
| Fecha | 2026-10-11 |
| Requisito asociado | RF05 |

## Historia
Como **usuario del sistema** (solicitante, coordinador o técnico), quiero **consultar las incidencias que me corresponden, con filtros, y ver su historial; y como coordinador, ver un tablero resumen**, para **saber en qué estado está cada caso y confiar en que el historial es fiel**.

## Alcance y exclusiones
**Incluye:** listado de incidencias con filtros por estado y prioridad según el rol, detalle con historial, registro de eventos de cada creación y transición exitosa, historial inmutable y tablero del coordinador.
**Excluye:** registro (S01), asignación (S02), atención (S03), validación (S04), edición o borrado de eventos, exportación, búsqueda por texto, notificaciones y adjuntos.

## Entradas
| Operación | Campo | Tipo | Obligatorio | Límites / valores permitidos |
|---|---|---|---|---|
| Listar | estado | texto | No | REGISTRADA, ASIGNADA, EN_ATENCION, PENDIENTE_VALIDACION, CERRADA |
| Listar | prioridad | texto | No | CRITICA, ALTA, NORMAL |
| Detalle | incidencia_id (en la ruta) | entero | Sí | Id de una incidencia existente |
| Tablero | (sin campos) | — | — | — |

Si se envían ambos filtros, se aplican juntos. El cliente nunca envía identidad, rol ni fecha.

El código INC-0001 es solo para mostrar en pantalla. Las rutas identifican la incidencia por su id entero (/incidencias/<int:incidencia_id>/...). Un id que no sea entero no coincide con la ruta (404).

## Precondiciones y permisos
- Usuario autenticado. Rol e identidad salen de la sesión en el servidor.
- **Solicitante:** ve solo las incidencias que él registró.
- **Técnico:** ve solo las incidencias asignadas a él.
- **Coordinador:** ve todas las incidencias.
- El detalle y el historial de una incidencia solo los ve quien tiene permiso de ver esa incidencia.
- El **tablero** es exclusivo del coordinador.

## Reglas y proceso
**Listado y detalle**
1. El servidor verifica sesión y obtiene el rol.
2. Aplica primero el alcance por rol y luego los filtros pedidos.
3. La prioridad no se guarda: se calcula con `calcular_prioridad(riesgo, impacto)` (CRITICA si hay riesgo; ALTA si no hay riesgo e impacto ALTO; NORMAL si no hay riesgo e impacto BAJO). El filtro por prioridad usa ese cálculo.
4. Un filtro con un valor fuera de la lista se rechaza.
5. En el detalle, si el id no existe responde 404; si existe pero no es del usuario o no es su asignación, responde 403.

**Historial**
1. Cada creación y cada transición exitosa (S01 a S04) guarda un evento con: autor, fecha UTC del servidor, estado anterior, estado nuevo y acción.
2. Los eventos de solución, rechazo, cierre y reapertura incluyen además la solución o el motivo correspondiente.
3. El historial se muestra en orden cronológico e incluye soluciones, motivos, cierres y reaperturas.
4. La tabla de eventos solo admite inserciones. No existen rutas para editar ni borrar eventos.
5. Una operación rechazada no genera evento.

**Tablero del coordinador**
1. Cantidad de incidencias por estado.
2. Cantidad de incidencias por prioridad.
3. Incidencias CRITICA que no están CERRADAS.
4. Porcentaje de cierre = incidencias en estado CERRADA / total de incidencias × 100, con un decimal. Con cero incidencias muestra `0,0 %`.
5. Una incidencia reabierta deja de contar como CERRADA, y su cierre anterior se conserva en el historial.

## Salidas y cambios persistidos
- Listado: incidencias visibles para el rol, con código (para mostrar), ubicación, categoría, estado y prioridad calculada.
- Detalle: datos de la incidencia y su historial completo.
- Tablero: los cuatro indicadores anteriores.
- Las consultas no modifican datos.

## Errores y efectos que deben evitarse
- Sin sesión: se redirige al login.
- Rol sin permiso (por ejemplo, un solicitante o técnico pide el tablero): 403.
- Incidencia existente pero ajena, o que no es su asignación: 403.
- Incidencia inexistente: 404.
- Filtro inválido: 400/422.
- Ninguna ruta permite editar o borrar eventos.
- Texto con HTML o scripts (descripciones, soluciones, motivos) se muestra escapado.
- Un historial nunca debe mostrar un evento de una operación que falló.

## Criterios de aceptación
- **AC-S05-01 (solicitante, alcance):** Dado dos solicitantes A y B con incidencias propias, cuando A lista incidencias, entonces ve solo las suyas y ninguna de B.
- **AC-S05-02 (técnico, alcance):** Dado incidencias asignadas a T01 y a T02, cuando T01 lista incidencias, entonces ve solo las asignadas a T01.
- **AC-S05-03 (coordinador, alcance):** Dado incidencias de varios solicitantes y técnicos, cuando el coordinador lista, entonces ve todas.
- **AC-S05-04 (filtro por estado):** Dado incidencias en distintos estados, cuando el coordinador filtra por estado CERRADA, entonces ve solo las CERRADA.
- **AC-S05-05 (filtro por prioridad):** Dado incidencias con riesgo, sin riesgo e impacto ALTO, y sin riesgo e impacto BAJO, cuando el coordinador filtra por prioridad CRITICA, entonces ve solo las que tienen riesgo para personas.
- **AC-S05-06 (filtros combinados y permisos):** Dado un solicitante con incidencias en varios estados y prioridades, cuando filtra por estado y prioridad a la vez, entonces ve solo las propias que cumplen ambos filtros.
- **AC-S05-07 (filtro inválido):** Dado un usuario autenticado, cuando filtra por estado "ABIERTA" o prioridad "URGENTE", entonces se rechaza con 400/422 y no se devuelve un listado.
- **AC-S05-08 (acceso ajeno al detalle):** Dado una incidencia existente del solicitante A, cuando el solicitante B o un técnico no asignado pide su detalle o su historial, entonces se rechaza con 403 y no se muestra ningún dato.
- **AC-S05-09 (historial completo):** Dado una incidencia que pasó por registro, asignación, atención, solución, rechazo, nueva solución, cierre y reapertura, cuando su dueño consulta el historial, entonces ve todos los eventos en orden, con autor, fecha, estados, acción, soluciones, motivos, cierres y reaperturas.
- **AC-S05-10 (inmutabilidad):** Dado un evento existente, cuando se intenta editarlo o borrarlo por cualquier ruta, entonces no existe esa operación, y el evento permanece igual.
- **AC-S05-11 (operación fallida sin evento):** Dado una operación rechazada (por permisos, estado, datos o plazo), cuando se consulta el historial, entonces no aparece ningún evento nuevo y el estado no cambió.
- **AC-S05-12 (tablero con datos):** Dado cuatro incidencias de las cuales una está CERRADA, cuando el coordinador abre el tablero, entonces muestra cantidades correctas por estado y por prioridad, las CRITICA no cerradas, y un porcentaje de cierre de `25,0 %`.
- **AC-S05-13 (tablero vacío):** Dado cero incidencias, cuando el coordinador abre el tablero, entonces el porcentaje de cierre es `0,0 %` y las cantidades son cero, sin error de división.
- **AC-S05-14 (reapertura y porcentaje):** Dado cuatro incidencias con una CERRADA (25,0 %), cuando su dueño la reabre, entonces el porcentaje baja a `0,0 %` y el cierre anterior sigue en el historial.
- **AC-S05-15 (tablero solo coordinador):** Dado un solicitante o un técnico autenticado, cuando intenta abrir el tablero, entonces se rechaza con 403.
- **AC-S05-16 (inexistente y sin sesión):** Dado un id de incidencia inexistente, cuando un usuario autenticado pide su detalle, entonces responde 404; y dado un visitante sin sesión, cuando intenta listar, ver un detalle o abrir el tablero, entonces se redirige al login. En ambos casos sin efectos.
- **AC-S05-17 (seguridad de texto):** Dado una incidencia con `<script>alert(1)</script>` en su descripción, solución o motivo, cuando se muestra en el listado, detalle o historial, entonces aparece como texto escapado sin ejecutarse.
- **AC-S05-18 (persistencia):** Dado incidencias y eventos guardados, cuando el servidor se reinicia, entonces el listado, el historial y el tablero muestran los mismos datos.

## Diseño y tareas vinculadas
| Tarea | Cubre |
|---|---|
| T-S05-1: ruta GET de listado con alcance por rol y filtros | AC-01 a 07, 16 |
| T-S05-2: ruta GET de detalle por `incidencia_id` con historial y control de acceso (404 inexistente, 403 ajena) | AC-08, 09, 16 |
| T-S05-3: tabla `eventos` de solo inserción, sin rutas de edición ni borrado | AC-09, 10, 11 |
| T-S05-4: función pura `calcular_prioridad(riesgo, impacto)` usada en listado y filtros | AC-05, 06 |
| T-S05-5: ruta GET del tablero (solo coordinador) con consultas agregadas | AC-12, 13, 14, 15 |
| T-S05-6: cálculo del porcentaje de cierre con un decimal y caso de cero registros | AC-12, 13, 14 |
| T-S05-7: plantillas Jinja con escape automático | AC-17 |
| T-S05-8: persistencia en SQLite (archivo de base de datos) | AC-18 |

## Pruebas y resultados esperados
Se automatizan en `tests/`: alcance por rol, filtros, historial tras flujo completo, inmutabilidad, tablero vacío (0,0 %), tablero con uno cerrado de cuatro (25,0 %), reapertura que reduce el porcentaje y persistencia tras reinicio. Resultado esperado: todos los AC cumplen. Se completa al ejecutar; si algo no se ejecuta, se declara pendiente.

## Decisión de revisión / versión aprobada
**Pendiente.** La revisión por otra persona no se ha realizado. No se registra como aprobada.
