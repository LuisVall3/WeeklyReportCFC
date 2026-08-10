"""
config.py

Manejador de configuración y rutas para la aplicación.
Mantiene el atributo .config que requiere la interfaz gráfica (gui.py).
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
        """Propiedad para obtener la ruta del maestro."""
        return self.config.get("rutas", {}).get("maestro", "")

    @property
    def ruta_semanal(self) -> str:
        """Propiedad para obtener la ruta del reporte semanal."""
        return self.config.get("rutas", {}).get("semanal", "")

    def rutas_validas(self) -> bool:
        """Verifica que la ruta del archivo maestro esté configurada y exista."""
        maestro = self.ruta_maestro
        if not maestro:
            return False
        return Path(maestro).exists()