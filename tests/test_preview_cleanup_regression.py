from pathlib import Path
import ast


def test_preview_detached_before_photoimage_released():
    source = Path(__file__).resolve().parents[1] / "src" / "whatsapp_tab.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "WhatsAppTab")
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "add_to_queue")
    lines = source.read_text(encoding="utf-8").splitlines()
    body = "\n".join(lines[fn.lineno - 1:fn.end_lineno])
    assert body.index("self.preview.configure(image=None") < body.index("self.preview_image = None")
    assert body.index("self._report_queue[park] =") < body.index("self.preview.configure(image=None")
