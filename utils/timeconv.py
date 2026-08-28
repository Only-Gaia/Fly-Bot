import re

TIME_REGEX = re.compile(r"(\d+)\s*([smhdw])", re.IGNORECASE)
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_duration(duration: str) -> int:
    """Converte una stringa tipo '1h30m' o '2d' in secondi totali."""
    matches = TIME_REGEX.findall(duration.lower())
    if not matches:
        raise ValueError("Formato durata non valido. Usa ad esempio: 10m, 1h, 2d, 1w")
    seconds = 0
    for value, unit in matches:
        seconds += int(value) * UNITS[unit]
    return seconds


def human_duration(seconds: int) -> str:
    """Converte dei secondi in una stringa leggibile tipo '1h 30m'."""
    parts = []
    for unit, unit_seconds in [("w", 604800), ("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]:
        value, seconds = divmod(seconds, unit_seconds)
        if value:
            parts.append(f"{value}{unit}")
    return " ".join(parts) if parts else "0s"
