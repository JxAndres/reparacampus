# SPEC S01 · Registrar incidencia

| Campo | Valor |
|---|---|
| Versión | 0.1 (borrador) |
| Autor | Juan (JxAndres) |
| Revisor | Pendiente (sin revisión de otra persona todavía) |
| Fecha | 2026-10-11 |
| Requisito asociado | RF01 |

## Historia
Como **solicitante**, quiero **registrar una incidencia de infraestructura**, para **que quede formalmente reportada y pueda ser priorizada y atendida**.

## Alcance y exclusiones
**Incluye:** formulario de registro, validación en servidor, generación de código, autor, fecha y estado inicial, y evento de creación en el historial.
**Excluye:** adjuntos, notificaciones, edición del reporte, asignación (S02).

## Entradas
| Campo | Tipo | Obligatorio | Límites / valores permitidos |
|---|---|---|---|
| ubicacion | texto | Sí | LAB-01, AULA-201, BIB-01 |
| categoria | texto | Sí | ELECTRICIDAD, HIDRAULICA, MOBILIARIO, TIC |
| descripcion | texto | Sí | 20 a 500 caracteres, después de quitar espacios externos |
| impacto | texto | Sí | BAJO o ALTO |
| riesgo_personas | booleano | Sí | true o false (no se acepta otro valor) |

## Precondiciones y permisos
- Usuario autenticado con rol SOLICITANTE. El rol y la identidad se obtienen de la sesión en el servidor, nunca del formulario.
- Coordinador y técnico no pueden registrar.

## Reglas y proceso
1. El servidor verifica sesión y rol.
2. Quita espacios externos de los textos y valida cada campo.
3. Si todo es válido, en **una sola transacción** crea la incidencia y su evento de historial.
4. El código, el autor (usuario de la sesión), la fecha (UTC, del servidor) y el estado REGISTRADA los genera el sistema.
5. La prioridad se calcula según S02 al registrar o consultar.

## Salidas y cambios persistidos
- Incidencia nueva: código único (ej. INC-0001), autor, fecha UTC, estado REGISTRADA.
- Evento de historial: acción CREAR, autor, fecha, estado anterior vacío, estado nuevo REGISTRADA.
- Respuesta de éxito con el código generado.

## Errores y efectos que deben evitarse
- Datos inválidos: se rechaza con mensaje claro; no se crea incidencia ni evento.
- Rol no permitido: se rechaza (403); sin efectos.
- Sin sesión: se redirige al login; sin efectos.
- Un fallo a mitad de la operación no deja incidencia sin evento ni evento sin incidencia.
- Texto con HTML o scripts se guarda como texto y se muestra escapado.

## Criterios de aceptación
- **AC-S01-01 (normal):** Dado un solicitante autenticado, cuando envía ubicación LAB-01, categoría TIC, descripción de 30 caracteres, impacto BAJO y riesgo false, entonces se crea una incidencia en estado REGISTRADA con código, autor y fecha generados, y un evento CREAR en el historial.
- **AC-S01-02 (permisos):** Dado un coordinador o un técnico autenticado, cuando intenta registrar una incidencia, entonces se rechaza con 403 y no se crea incidencia ni evento.
- **AC-S01-03 (datos inválidos):** Dado un solicitante autenticado, cuando envía impacto "MEDIO", o riesgo distinto de booleano, o ubicación o categoría fuera de la lista, o un campo vacío, entonces se rechaza y no se persiste nada.
- **AC-S01-04 (límite inferior):** Dado un solicitante autenticado, cuando envía una descripción de 19 caracteres, entonces se rechaza; con 20 caracteres, se acepta.
- **AC-S01-05 (límite superior):** Dado un solicitante autenticado, cuando envía una descripción de 500 caracteres se acepta, y con 501 se rechaza.
- **AC-S01-06 (espacios externos):** Dado un solicitante autenticado, cuando envía una descripción con 19 caracteres útiles más espacios al inicio y al final, entonces se rechaza porque los límites se aplican tras retirar espacios.
- **AC-S01-07 (sin sesión):** Dado un visitante sin sesión, cuando intenta registrar, entonces se redirige al login y no se crea nada.
- **AC-S01-08 (seguridad de texto):** Dado un solicitante autenticado, cuando registra una descripción con `<script>alert(1)</script>` de 20 o más caracteres, entonces se guarda como texto y se muestra escapado sin ejecutarse.
- **AC-S01-09 (atomicidad):** Dado un fallo simulado al guardar el evento, cuando se registra una incidencia, entonces no queda ninguna incidencia sin su evento.

## Diseño y tareas vinculadas
| Tarea | Cubre |
|---|---|
| T-S01-1: tabla `incidencias` y `eventos` en el esquema SQL | AC-01, 09 |
| T-S01-2: ruta POST `/incidencias` con validación en servidor | AC-01 a 06 |
| T-S01-3: decorador de rol y sesión | AC-02, 07 |
| T-S01-4: plantilla Jinja con escape automático | AC-08 |
| T-S01-5: transacción única incidencia + evento | AC-09 |

## Pruebas y resultados esperados
Se automatizan en `tests/` (ver Parte 3). Resultado esperado: todos los AC cumplen. Se completa al ejecutar.

## Decisión de revisión / versión aprobada
**Pendiente.** La revisión por otra persona no se ha realizado. Se declara como pendiente; no se registra como aprobada.