"""Pruebas de regresión NovaCommand CCTV. Ejecutar: python -m pytest -v tests/"""
import ast
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def source(module):
    return (ROOT / 'src' / (module + '.py')).read_text(encoding='utf-8')

def test_python_syntax_all_modules():
    for file in [ROOT / 'app.py', * (ROOT / 'src').glob('*.py')]:
        ast.parse(file.read_text(encoding='utf-8'), filename=str(file))

def test_icon_is_real_ico():
    assert (ROOT / 'assets' / 'favicon.ico').read_bytes()[:4] == b'\x00\x00\x01\x00'

def test_batch_reuses_one_chrome_session():
    tree = ast.parse(source('whatsapp_sender'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'send_reports_batch')
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
    chrome = [n for n in calls if isinstance(n.func, ast.Attribute) and n.func.attr == 'Chrome']
    assert len(chrome) == 1
    assert any(isinstance(n, ast.For) and isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Name) and n.iter.func.id == 'enumerate' for n in ast.walk(fn))

def test_batch_no_history_check():
    assert 'verify_history=False' in source('whatsapp_sender')
    assert 'time.sleep(20)' in source('whatsapp_sender')

def test_span_results_are_deduplicated():
    src = source('whatsapp_sender')
    assert 'seen_rows = set()' in src
    assert 'if row.id in seen_rows:' in src
    assert 'if len(matches) != 1:' in src

def test_language_support():
    src = source('whatsapp_sender').lower()
    assert 'photos & videos' in src
    assert 'fotos y videos' in src

def test_queue_clears_novelty_and_camera_count():
    src = source('whatsapp_tab')
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'WhatsAppTab')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'add_to_queue')
    body = ast.get_source_segment(src, fn)
    assert "self.novedades.delete('1.0', 'end')" in body
    assert "self.cameras.set('0')" in body

def test_queue_does_not_reuse_previous_photo():
    src = source('whatsapp_tab')
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'WhatsAppTab')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'add_to_queue')
    assignments = [n for n in ast.walk(fn) if isinstance(n, (ast.Assign, ast.AnnAssign))]
    assert any(isinstance(t, ast.Attribute) and t.attr == 'image' and isinstance(t.value, ast.Name) and t.value.id == 'self' and isinstance(n.value, ast.Constant) and n.value.value is None for n in assignments for t in (n.targets if isinstance(n, ast.Assign) else [n.target])), 'La imagen no se limpia: riesgo de reutilizar la captura del parque anterior.'

def test_no_single_send_button():
    src = source('whatsapp_tab')
    assert "text='Enviar reporte a WhatsApp'" not in src

# Pruebas de integración con Selenium simulado: requieren dependencias instaladas.
def test_batch_two_parks_without_real_whatsapp(tmp_path, monkeypatch):
    pytest.importorskip('selenium')
    from src import whatsapp_sender as w
    images = []
    for name in ('Parque A', 'Parque B'):
        p = tmp_path / (name + '.png')
        p.write_bytes(b'fake image - no decoding in mocked batch')
        images.append({'park': name, 'message': name + ' reporte', 'image_path': str(p)})
    class Driver:
        def __init__(self): self.closed = False
        def get(self, url): self.url = url
        def quit(self): self.closed = True
    class Wait:
        def until(self, f): return True
    drivers = []
    def create(options):
        d = Driver(); drivers.append(d); return d
    calls = []
    monkeypatch.setattr(w.webdriver, 'Chrome', create)
    monkeypatch.setattr(w, 'esperar', lambda *a, **kw: Wait())
    monkeypatch.setattr(w, 'abrir_grupo', lambda *a: None)
    monkeypatch.setattr(w, 'verificar_destinatario', lambda *a: None)
    monkeypatch.setattr(w, 'enviar_imagen', lambda d, g, p, m, verify_history: calls.append((p,m,verify_history)) or True)
    monkeypatch.setattr(w.time, 'sleep', lambda n: None)
    result = w.send_reports_batch('Prueba', images, profile_dir=tmp_path / 'profile')
    assert len(drivers) == 1 and drivers[0].closed
    assert len(calls) == 2 and all(x[2] is False for x in calls)
    assert [r['status'] for r in result] == ['procesado','procesado']

def test_batch_stops_on_uncertain_send(tmp_path, monkeypatch):
    pytest.importorskip('selenium')
    from src import whatsapp_sender as w
    paths = []
    for i in range(3):
        p = tmp_path / f'{i}.png';p.write_bytes(b'x');paths.append({'park':f'P{i}','message':f'M{i}','image_path':str(p)})
    class Driver:
        def get(self, url): pass
        def quit(self): pass
    class Wait:
        def until(self, f): return True
    calls=[]
    monkeypatch.setattr(w.webdriver,'Chrome',lambda options: Driver())
    monkeypatch.setattr(w,'esperar',lambda *a,**kw: Wait())
    monkeypatch.setattr(w,'abrir_grupo',lambda *a:None)
    monkeypatch.setattr(w,'verificar_destinatario',lambda *a:None)
    monkeypatch.setattr(w,'enviar_imagen',lambda d,g,p,m,verify_history: calls.append(p) or False)
    monkeypatch.setattr(w.time,'sleep',lambda n:None)
    results=w.send_reports_batch('Prueba',paths,profile_dir=tmp_path/'profile')
    assert len(calls)==1
    assert [r['status'] for r in results]==['sin_confirmar','pendiente','pendiente']


def test_queue_clears_image_only_after_successful_add(tmp_path, monkeypatch):
    from unittest.mock import Mock
    from PIL import Image
    from src import whatsapp_tab as mod
    class Var:
        def __init__(self, value): self.value = value
        def get(self): return self.value
        def set(self, value): self.value = value
    class Text:
        def __init__(self, value): self.value = value
        def get(self, *args): return self.value
        def delete(self, *args): self.value = ''
    tab = object.__new__(mod.WhatsAppTab)
    tab._sending = False
    tab.park = Var('CL118 Villa Seca')
    tab.date = Var('16-10-2026')
    tab.time = Var('12:00')
    tab.cameras = Var('4')
    tab.novedades = Text('Sin novedades')
    tab.operador_cctv = Var('Matías Guzmán')
    tab.image = Image.new('RGB',(12,12),'red')
    tab.image_path = 'old.png'
    tab.preview_image = object()
    tab.preview = Mock()
    tab.batch_button = Mock()
    tab.status = Mock()
    tab._report_queue = {}
    tab._update_availability = Mock()
    monkeypatch.setattr(mod, 'ROOT', tmp_path)
    tab.add_to_queue()
    assert len(tab._report_queue) == 1
    saved = next(iter(tab._report_queue.values()))
    assert Path(saved['image_path']).exists()
    assert tab.image is None and tab.image_path is None and tab.preview_image is None
    tab.preview.configure.assert_called_with(image=None, text='Sin captura adjunta')
    assert tab.cameras.get() == '0' and tab.novedades.get() == ''
