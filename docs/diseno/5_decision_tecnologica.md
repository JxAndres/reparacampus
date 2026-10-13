# Decisión de diseño: monolito modular en Flask con SQLite

**Autor:** Antonio · **Versión:** 0.2 · **Fecha:** 2026-10-12 · **Estado:** para revisión de Keyner (PR #9)

## Contexto
ReparaCampus es un prototipo con tres roles y cinco funcionalidades (S01 a S05), desarrollado en una semana por cinco personas. Exige reglas estrictas (siete transiciones de estado, plazo de 48 h, permisos por rol y dueño), historial inmutable y operaciones sin efectos parciales. No requiere hosting, notificaciones, adjuntos ni IA dentro del producto.

## Decisión
Un **monolito modular** con Python, Flask y SQLite. Cada funcionalidad vive en su propio módulo (blueprint) y piezas pequeñas compartidas evitan repetir reglas.

| Pieza | Responsabilidad |
|---|---|
| `auth.py` | Login, logout, sesión del servidor y decoradores `login_required` y `rol_requerido`. Rol e identidad salen de la sesión, no del formulario. |
| `incidencias.py`, `asignaciones.py`, `atencion.py` | Un módulo por funcionalidad (S01, S02, S03). Cada uno junta la ruta, la función de negocio y las consultas SQL. |
| `prioridad.py` | `calcular_prioridad(riesgo, impacto)`: función pura. La prioridad no se guarda. |
| `reloj.py` | `ahora()` en UTC, reemplazable en pruebas. |
| `db.py` | Abre la conexión SQLite con claves foráneas activas. |
| `schema.sql` | Tablas, restricciones CHECK y triggers que impiden editar o borrar eventos. |

Las funciones de negocio reciben la conexión y la hora (`momento`) como parámetros y cambian estado, registros e historial dentro de `with conn`, que es una **transacción única**: si algo falla, no queda nada a medias.

### Arquitectura implementada y arquitectura objetivo
En una primera versión de este documento se describieron tres capas separadas (rutas, servicios por funcionalidad y repositorios SQL) y un decorador de dueño. **Eso no es lo que el código implementa hoy.** El prototipo usa una versión simplificada:

- Rutas, reglas y SQL conviven en cada módulo; no hay capa de servicios ni de repositorios.
- Solo existe `rol_requerido`. El control de dueño de S04 (y el de técnico asignado, que hoy se hace dentro de `atencion.py`) necesita consultar la base de datos, por lo que se implementará dentro de la función de negocio o con un decorador nuevo.
- La separación en tres capas queda como **arquitectura objetivo** si el sistema creciera.

## Alternativas consideradas
| Alternativa | Ventaja | Por qué no se eligió |
|---|---|---|
| Tres capas estrictas (rutas, servicios, repositorios) | Reglas aisladas del SQL; cambiar de motor es más fácil | Más archivos y más código para cinco funcionalidades y una semana de plazo |
| Frontend React con API REST separada | Interfaz más rica | Doble despliegue; el enunciado no exige React |
| Microservicios | Escalado independiente | Complejidad desproporcionada para el alcance |
| PostgreSQL | Mejor concurrencia | Requiere instalar un servidor; SQLite es un archivo y se reproduce con un comando |
| Reglas en JavaScript del cliente | Respuesta inmediata | Insegura: el cliente puede manipularse; el servidor debe validar |
| Estado e historial en operaciones separadas | Código más simple | Puede dejar un estado sin evento; se descarta frente a la transacción única |

## Consecuencias
**Positivas**
- Poco código y fácil de seguir: cada funcionalidad es un módulo.
- Las funciones de negocio se prueban sin navegador, pasando la conexión y la hora.
- La transacción única garantiza que estado e historial se guardan juntos o no se guardan.
- El historial es inmutable también en la base de datos: los triggers `eventos_no_update` y `eventos_no_delete` abortan cualquier UPDATE o DELETE sobre `eventos`.
- Las restricciones CHECK del esquema (estados, acciones, límites de texto) actúan como segunda línea de defensa.

**Negativas y límites aceptados**
- El SQL está mezclado con las reglas de negocio: cambiar de motor de base de datos exige editar los módulos.
- El reloj reemplazable depende de cómo cada módulo lo importa. `incidencias.py` y `asignaciones.py` hacen `from app.reloj import ahora`, de modo que reemplazar `app.reloj.ahora` no cambia lo que ellos usan; `atencion.py` usa `reloj.ahora()`. Para probar el plazo de 48 h, las funciones de S04 deben recibir `momento` como parámetro (como S01 a S03) o usar `reloj.ahora()`.
- SQLite admite poca concurrencia de escritura: aceptable para un prototipo.
- Todo se despliega junto: un error grave afecta a toda la aplicación.

## Trazabilidad
Requisitos RF01 a RF05 → SPECS S01 a S05 → diagramas de estados, datos, secuencia y componentes → código → pruebas.
