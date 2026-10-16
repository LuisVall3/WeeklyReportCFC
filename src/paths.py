"""Rutas persistentes para NovaCommand CCTV."""
import os
import sys
from pathlib import Path

APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "NovaCommand CCTV" if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
APP_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
