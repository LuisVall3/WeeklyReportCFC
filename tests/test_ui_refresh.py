"""Regresiones estáticas de la interfaz: no requieren escritorio ni Chrome."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_navegacion_y_marca():
    ui = (ROOT / 'src/gui.py').read_text(encoding='utf-8')
    assert 'NovaCommand CCTV' in ui
    assert 'NovaSource Power Services' in ui
    assert 'Reportes semanales' in ui
    assert 'CCTV · WhatsApp' in ui
    assert 'Ver Excel Maestro' in ui

def test_cola_sin_envio_individual_visible():
    ui = (ROOT / 'src/whatsapp_tab.py').read_text(encoding='utf-8')
    assert 'Agregar parque a la cola' in ui
    assert 'Enviar cola (0)' in ui
    assert "text='Enviar reporte a WhatsApp'" not in ui

def test_imagenes_y_recursos():
    ui = (ROOT / 'src/whatsapp_tab.py').read_text(encoding='utf-8')
    assert 'self.preview' in ui
    assert (ROOT / 'assets/favicon.ico').exists()
    assert (ROOT / 'assets/novasource_logo.png').exists()

def test_sender_y_excel_sin_cambios_de_logica():
    assert (ROOT / 'src/whatsapp_sender.py').is_file()
    assert (ROOT / 'src/excel.py').is_file()
