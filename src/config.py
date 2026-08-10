"""
config.py

Manejador de configuración y rutas para la aplicación.
Guarda y carga las rutas en config.json.
"""

import json
from pathlib import Path


class ConfigManager:

    def __init__(self, config_file: str = "config.json"):
        self.config_path = Path(config_file)
        self.config = {
            "rutas": {
                "maestro": "",
                "semanal": ""
            }
        }
        self.cargar_config()

    def cargar_config(self):
        """Carga las rutas desde el archivo json si existe."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.config = data
            except Exception:
                pass

    def guardar_config(self, ruta_maestro: str, ruta_semanal: str = ""):
        """Guarda las rutas en el archivo json."""
        if "rutas" not in self.config:
            self.config["rutas"] = {}

        self.config["rutas"]["maestro"] = ruta_maestro
        self.config["rutas"]["semanal"] = ruta_semanal

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    @property
    def ruta_maestro(self) -> str:
        return self.config.get("rutas", {}).get("maestro", "")

    @property
    def ruta_semanal(self) -> str:
        return self.config.get("rutas", {}).get("semanal", "")

    def rutas_validas(self) -> bool:
        """Comprueba si la ruta del maestro está configurada y el archivo existe."""
        maestro = self.ruta_maestro
        if not maestro:
            return False
        # Convertimos siempre a Path para evitar 'str object has no attribute exists'
        return Path(maestro).exists()