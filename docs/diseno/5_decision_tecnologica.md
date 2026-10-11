# Decisión de diseño: monolito modular en Flask con SQLite

**Autor:** Antonio · **Fecha:** 2026-10-11 · **Estado:** borrador para revisión del equipo

## Contexto
ReparaCampus es un prototipo con tres roles, cinco funcionalidades (S01 a S05) y una semana de trabajo para cinco integrantes. Requiere reglas de negocio estrictas (siete transiciones de estado, plazo de 48 h, permisos por rol y dueño), historial inmutable y operaciones sin efectos parciales. No requiere hosting, notificaciones, adjuntos ni IA dentro del producto.

## Decisión
Se construye un **monolito modular** con Python, Flask y SQLite, organizado en tres capas:
1. **Rutas:** sesión, decoradores de rol y dueño, plantillas Jinja.
2. **Lógica de negocio:** servicios por funcionalidad, `calcular_prioridad` (función pura), validaciones y reloj inyectable.
3. **Persistencia:** repositorios SQL con una transacción por operación.

Las reglas se ejecutan en el servidor; la interfaz HTML/CSS/JavaScript solo presenta y envía datos. Ocultar un botón nunca reemplaza un control de permisos.

## Alternativas consideradas
| Alternativa | Ventaja | Por qué no se eligió |
|---|---|---|
| Frontend React + API REST separada | Interfaz más rica, separación fuerte | Doble despliegue y más trabajo para un alcance de una semana; el enunciado no exige React |
| Microservicios | Escalado independiente | Complejidad desproporcionada para 5 funcionalidades y un solo equipo |
| PostgreSQL | Concurrencia y escalabilidad | Requiere instalar y configurar un servidor; SQLite es un solo archivo y reproduce el entorno con un comando |
| Reglas en JavaScript del cliente | Respuesta inmediata | Insegura: el cliente puede manipularse; el enunciado exige validar en servidor |
| Estado y historial en operaciones separadas | Código más simple | Puede dejar estados sin evento; se descarta frente a la transacción única |

## Consecuencias
**Positivas**
- Un solo proyecto, fácil de ejecutar y probar desde una copia limpia.
- Las capas permiten probar la lógica sin la interfaz (pytest y cliente de pruebas de Flask).
- La transacción única garantiza que estado e historial se guardan juntos o no se guarda nada.
- Un reloj inyectable permite probar exactamente 48 h y un instante después, sin esperar.

**Negativas y límites aceptados**
- SQLite soporta poca concurrencia de escritura: aceptable para un prototipo.
- Todo se despliega junto: un error grave afecta a toda la aplicación.
- La interfaz con plantillas es menos dinámica que una SPA.
- Si el sistema creciera, habría que migrar a PostgreSQL y separar capas en servicios; la división en tres capas facilita ese paso.

## Trazabilidad
Requisitos RF01 a RF05 → SPECS S01 a S05 → diagramas de estados, datos, secuencia y componentes → código → pruebas.
