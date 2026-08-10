"""
backup.py

Mapeo y creación de copias de seguridad de resguardo.
"""

from pathlib import Path
from shutil import copy2
from datetime import datetime


class BackupManager:

    def __init__(self, archivo_maestro: Path):
        self.archivo_maestro = archivo_maestro

    def crear_backup(self) -> Path:
        """
        Crea una copia de seguridad del archivo maestro con marca de tiempo.
        Lanza un PermissionError legible si el archivo está abierto por Excel/OneDrive.
        """
        if not self.archivo_maestro.exists():
            raise FileNotFoundError(f"No se encontró el archivo maestro en: {self.archivo_maestro}")

        # Carpeta donde se guardarán los backups
        dir_backup = self.archivo_maestro.parent / "Backups_Weekly_Report"
        dir_backup.mkdir(parents=True, exist_ok=True)

        # Nombre con timestamp (ejemplo: Weekly Report 2026_backup_20260810_014600.xlsx)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_backup = f"{self.archivo_maestro.stem}_backup_{timestamp}{self.archivo_maestro.suffix}"
        ruta_backup = dir_backup / nombre_backup

        try:
            copy2(self.archivo_maestro, ruta_backup)
            return ruta_backup
        except PermissionError:
            raise PermissionError(
                f"No se pudo crear la copia de seguridad porque el archivo está siendo usado por otro programa.\n\n"
                f"Por favor, CIERRA el archivo Excel '{self.archivo_maestro.name}' e intenta nuevamente."
            )