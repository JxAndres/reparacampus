from datetime import datetime, timezone


def ahora():
    """Hora actual en UTC. Las pruebas pueden reemplazar esta función."""
    return datetime.now(timezone.utc)