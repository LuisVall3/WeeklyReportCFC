"""
Punto de entrada principal para la aplicación ejecutable.
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al PATH de Python
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import ConfigManager
from src.app import App  # <--- AQUÍ ESTÁ EL CAMBIO (App en lugar de CarbonFreeApp)
from src.gui import MainWindow, SetupDialog


def main():
    config_mgr = ConfigManager()

    # Si no están configuradas las rutas iniciales, mostrar diálogo de Setup
    if not config_mgr.rutas_validas():
        setup = SetupDialog(config_mgr)
        setup.mainloop()

    # Si el usuario configuró correctamente las rutas, iniciar la App Principal
    if config_mgr.rutas_validas():
        core_app = App(config_mgr)
        window = MainWindow(core_app)
        window.mainloop()


if __name__ == "__main__":
    main()