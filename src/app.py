"""
app.py

Controlador principal de la aplicación CCTV Weekly Report CFC.
Coordina la validación, respaldo e importación de registros en el Excel Maestro.
"""

from pathlib import Path
from typing import Callable
from src.config import ConfigManager
from src.backup import BackupManager
from src.excel import ExcelManager


class App:

    def __init__(self, config: ConfigManager):
        self.config = config
        self.backup = BackupManager(self.config.ruta_maestro)
        self.excel = ExcelManager(self.config.ruta_maestro)

    def run(self, log_callback: Callable[[str], None], ruta_archivo: str):
        """
        Flujo principal de procesamiento:
        1. Validar existencia del archivo maestro
        2. Crear copia de seguridad (Backup)
        3. Procesar reporte semanal e insertar/actualizar registros por hoja WW
        """
        archivo_nuevo = Path(ruta_archivo)

        log_callback(f"INICIO: Procesando archivo -> {archivo_nuevo.name}")

        # 1. Validar que el archivo maestro configurado exista
        if not self.excel.existe():
            raise FileNotFoundError(
                f"No se encontró el archivo Excel Maestro en la ruta:\n{self.config.ruta_maestro}\n"
                "Verifica la configuración inicial."
            )

        # 2. Respaldar Excel Maestro antes de editar
        log_callback("BACKUP: Creando copia de seguridad del Excel Maestro...")
        try:
            ruta_backup = self.backup.crear_backup()
            log_callback(f"BACKUP CREADO: {ruta_backup.name}")
        except PermissionError as pe:
            # Captura directa si el Excel maestro está abierto por el usuario
            raise PermissionError(str(pe))
        except Exception as e:
            log_callback(f"WARNING: No se pudo crear el backup ({e}). Continuando procesamiento...")

        # 3. Procesar y agregar registros al Excel Maestro
        log_callback("EXCEL: Leyendo reporte semanal y actualizando hoja Monitoreo WW...")
        
        try:
            total_procesados = self.excel.agregar_registros(archivo_nuevo)
            log_callback(f"EXCEL: Se actualizaron/insertaron {total_procesados} registros de parques exitosamente.")
            log_callback("ÉXITO: Archivo Maestro guardado correctamente.")
        except Exception as e:
            log_callback(f"ERROR EXCEL: Fallo al escribir en el archivo maestro: {e}")
            raise e