"""
Storage semplice basato su file JSON.
Ogni cog usa un proprio file (es: warns.json, economy.json, xp.json...) così
i dati restano separati e leggibili. Non serve un database esterno.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


class Storage:
    def __init__(self, filename: str):
        self.path = DATA_DIR / filename
        if not self.path.exists():
            self._write({})
        self.data = self._read()

    def _read(self) -> dict:
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def _write(self, data: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def save(self) -> None:
        self._write(self.data)

    def get(self, *keys, default=None):
        """Storage.get(guild_id, user_id, default=0)"""
        d = self.data
        for k in keys:
            k = str(k)
            if not isinstance(d, dict) or k not in d:
                return default
            d = d[k]
        return d

    def set(self, *keys_and_value):
        """Storage.set(guild_id, user_id, 100) -> imposta il valore finale"""
        *keys, value = keys_and_value
        d = self.data
        for k in keys[:-1]:
            k = str(k)
            d = d.setdefault(k, {})
        d[str(keys[-1])] = value
        self.save()

    def delete(self, *keys):
        d = self.data
        for k in keys[:-1]:
            k = str(k)
            if k not in d:
                return
            d = d[k]
        d.pop(str(keys[-1]), None)
        self.save()
