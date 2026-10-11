# Preguntas al cliente y supuestos

**Proyecto:** ReparaCampus · **Versión:** 1.0 · **Autor:** Juan (JxAndres)

## 1. Necesidad, actores y alcance

**Necesidad:** la Universidad Simón Bolívar recibe reportes de daños por varios
canales y a veces cierra incidencias sin confirmar que quedaron resueltas.
Se requiere un prototipo para registrar, priorizar, asignar y validar la solución.

**Actores:**
| Actor | Responsabilidad |
|---|---|
| Solicitante | Registra incidencias, consulta las propias, confirma, rechaza o reabre la solución |
| Coordinador | Consulta todas las incidencias y asigna un técnico |
| Técnico | Consulta sus asignaciones, inicia la atención y registra la solución |

**Alcance:** RF01 a RF05 del enunciado. Sin adjuntos, notificaciones, hosting ni IA en el producto.

## 2. Tres preguntas al cliente

| # | Pregunta | Por qué importa | Respuesta / estado |
|---|---|---|---|
| P1 | Cuando el solicitante rechaza una solución, ¿el técnico debe ver el motivo del rechazo al volver la incidencia a EN_ATENCION? | Define qué datos se muestran al técnico | Pendiente |
| P2 | ¿El coordinador puede ver la solución y el historial completo de cualquier incidencia, o solo el estado? | Define permisos de lectura (RF05) | Pendiente |
| P3 | Si una incidencia se reabre varias veces, ¿las 48 h se cuentan siempre desde el último cierre? | Define el cálculo del plazo en RF04 | Pendiente: el enunciado indica "último cierre" |

## 3. Supuestos pendientes

Una respuesta de IA no es una decisión del cliente. Estos supuestos están **sin confirmar** con el cliente:

| # | Supuesto | Estado |
|---|---|---|
| A1 | El técnico ve el motivo del rechazo y la solución anterior | Sin confirmar |
| A2 | El coordinador ve el historial completo de todas las incidencias | Sin confirmar |
| A3 | Las 48 h se cuentan desde el último cierre (según enunciado) | Respaldado por el enunciado |
| A4 | El solicitante ve solo sus incidencias; el técnico solo las asignadas a él | Sin confirmar |
| A5 | Los espacios al inicio y al final del texto se eliminan antes de validar longitudes | Respaldado por el enunciado |