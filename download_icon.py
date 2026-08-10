import os
import subprocess
from pathlib import Path

assets_dir = Path("assets")
assets_dir.mkdir(exist_ok=True)

# Ruta de la imagen cargada
origen = Path("logo_original.jpeg")
png_dest = assets_dir / "novasource_logo.png"
ico_dest = assets_dir / "favicon.ico"

if not origen.exists():
    print("⚠️ Por favor coloca la imagen guardada como 'logo_original.jpeg' en la raíz del proyecto.")
else:
    print("Procesando imagen con la herramienta nativa de macOS...")
    
    # Convertir a PNG usando la herramienta del sistema en macOS (sips)
    cmd_png = f"sips -s format png '{origen}' --out '{png_dest}'"
    subprocess.run(cmd_png, shell=True, check=True)
    
    # Crear copia como favicon.ico
    cmd_ico = f"cp '{png_dest}' '{ico_dest}'"
    subprocess.run(cmd_ico, shell=True, check=True)

    print(f"¡Listo! Logo de NovaSource guardado en:\n - {png_dest}\n - {ico_dest}")