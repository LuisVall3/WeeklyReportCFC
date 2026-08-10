# src/backup.py
from pathlib import Path
from datetime import datetime
import shutil

class BackupManager:
    def __init__(self, ruta_maestro):
        self.ruta_maestro = Path(ruta_maestro) if ruta_maestro else None

    def crear_backup(self) -> Path:
        if not self.ruta_maestro or not self.ruta_maestro.exists():
            raise FileNotFoundError(f"No existe el archivo maestro para respaldar: {self.ruta_maestro}")
        
        carpeta_backup = self.ruta_maestro.parent / "backups"
        carpeta_backup.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_backup = f"{self.ruta_maestro.stem}_backup_{timestamp}{self.ruta_maestro.suffix}"
        ruta_dest = carpeta_backup / nombre_backup
        
        shutil.copy2(self.ruta_maestro, ruta_dest)
        return ruta_dest