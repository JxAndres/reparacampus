def calcular_prioridad(riesgo_personas, impacto):
    """Función pura: la prioridad nunca se guarda ni la envía el cliente."""
    if impacto not in ("BAJO", "ALTO"):
        raise ValueError("Impacto no válido")
    if riesgo_personas:
        return "CRITICA"
    if impacto == "ALTO":
        return "ALTA"
    return "NORMAL"