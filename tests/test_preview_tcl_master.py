from pathlib import Path


def test_preview_image_belongs_to_preview_widget():
    source = (Path(__file__).resolve().parents[1] / "src" / "whatsapp_tab.py").read_text(encoding="utf-8")
    assert "ImageTk.PhotoImage(resized, master=self.preview)" in source
    assert "self.preview.configure(image=new_preview, text='')" in source

def test_preview_reset_detaches_before_release():
    source = (Path(__file__).resolve().parents[1] / "src" / "whatsapp_tab.py").read_text(encoding="utf-8")
    start = source.index("def add_to_queue(") if "def add_to_queue(" in source else source.index("self.preview.configure(image=None, text='Sin captura adjunta')")
    segment = source[start:]
    assert segment.index("self.preview.configure(image=None, text='Sin captura adjunta')") < segment.index("self.preview_image = None")
