import os
import sys
import traceback
from pathlib import Path
from typing import Optional
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageEnhance

# Windows agrupa las ventanas Tk por identidad de aplicación.
# Registrar un AppUserModelID propio antes de crear cualquier ventana.
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "NovaSource.PowerServices.WeeklyReportCFC"
        )
    except (AttributeError, OSError) as exc:
        print(f"No se pudo registrar el identificador de la aplicación: {exc}")

# Configuración de tema Corporativo / Claro
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


def resource_path(relative_path: str) -> Path:
    """Ruta de recursos en desarrollo y en ejecutables de PyInstaller."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / relative_path


def aplicar_icono_ventana(window):
    """Aplica el favicon de NovaSource sin reemplazarlo por el logo grande."""
    ico = resource_path("assets/favicon.ico")

    def _apply():
        if not ico.is_file():
            print(f"Falta el ícono: {ico}")
            return
        try:
            # Para Windows, el ICO es el icono de la ventana y de la barra.
            window.iconbitmap(default=str(ico))
        except Exception as exc:
            print(f"No se pudo cargar favicon.ico: {exc}")

    window.after(150, _apply)


def cargar_logo_fondo(ancho: int = 240, opacidad: float = 0.05) -> Optional[ctk.CTkImage]:
    """Carga el logo y le aplica una opacidad muy suave (marca de agua)."""
    ruta_png = resource_path("assets/novasource_logo.png")

    if not ruta_png.exists():
        return None

    try:
        img = Image.open(ruta_png).convert("RGBA")
        ratio = ancho / float(img.size[0])
        alto = int((float(img.size[1]) * float(ratio)))
        img = img.resize((ancho, alto), Image.Resampling.LANCZOS)

        alpha = img.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacidad)
        img.putalpha(alpha)

        return ctk.CTkImage(light_image=img, dark_image=img, size=(ancho, alto))
    except Exception as e:
        print(f"No se pudo cargar el logo de fondo: {e}")
        return None


class SetupDialog(ctk.CTk):
    """Ventana inicial de configuración de rutas."""

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager

        self.title("Configuración Inicial - NovaSource CFC")
        self.geometry("580x380")
        self.resizable(False, False)
        self.configure(fg_color="#F4F6F8")

        aplicar_icono_ventana(self)
        self.protocol("WM_DELETE_WINDOW", self._cerrar_limpio)

        self.frame = ctk.CTkFrame(
            self,
            corner_radius=8,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E0E0E0"
        )
        self.frame.pack(fill="both", expand=True, padx=24, pady=24)

        self.lbl_title = ctk.CTkLabel(
            self.frame,
            text="Configuración del Sistema",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#1A252C"
        )
        self.lbl_title.pack(anchor="w", padx=24, pady=(20, 4))

        self.lbl_subtitle = ctk.CTkLabel(
            self.frame,
            text="Selecciona la ubicación del Excel Maestro para iniciar las operaciones.",
            font=ctk.CTkFont(size=12),
            text_color="#5F6D7A"
        )
        self.lbl_subtitle.pack(anchor="w", padx=24, pady=(0, 20))

        self.lbl_maestro = ctk.CTkLabel(
            self.frame,
            text="Archivo Excel Maestro (.xlsx)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50"
        )
        self.lbl_maestro.pack(anchor="w", padx=24, pady=(5, 4))

        self.frame_maestro = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.frame_maestro.pack(fill="x", padx=24, pady=(0, 20))

        ruta_inicial_maestro = getattr(self.config_manager, "ruta_maestro", None)
        self.entry_maestro = ctk.CTkEntry(
            self.frame_maestro,
            placeholder_text="Seleccionar ruta del Excel Maestro...",
            fg_color="#F8F9FA",
            border_color="#CED4DA",
            text_color="#1A252C",
            height=36
        )
        self.entry_maestro.pack(side="left", fill="x", expand=True, padx=(0, 10))
        if ruta_inicial_maestro:
            self.entry_maestro.insert(0, str(ruta_inicial_maestro))

        self.btn_browse_maestro = ctk.CTkButton(
            self.frame_maestro,
            text="Buscar...",
            width=90,
            height=36,
            fg_color="#4A5568",
            hover_color="#2D3748",
            text_color="#FFFFFF",
            command=self._buscar_maestro
        )
        self.btn_browse_maestro.pack(side="right")

        self.btn_guardar = ctk.CTkButton(
            self.frame,
            text="Guardar y Continuar",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0D47A1",
            hover_color="#0A3880",
            text_color="#FFFFFF",
            command=self._guardar
        )
        self.btn_guardar.pack(fill="x", padx=24, pady=(15, 20))

    def _buscar_maestro(self):
        filename = filedialog.askopenfilename(
            title="Seleccionar Excel Maestro",
            filetypes=[("Archivos de Excel", "*.xlsx *.xlsm")]
        )
        if filename:
            self.entry_maestro.delete(0, "end")
            self.entry_maestro.insert(0, filename)

    def _guardar(self):
        ruta = self.entry_maestro.get().strip()
        if not ruta:
            messagebox.showwarning("Atención", "Por favor selecciona la ruta del Excel Maestro.")
            return

        if not os.path.exists(ruta):
            messagebox.showerror("Error", "La ruta seleccionada no existe.")
            return

        self.config_manager.guardar_config(ruta)
        self._cerrar_limpio()

    def _cerrar_limpio(self):
        try:
            self.withdraw()
            self.quit()
            self.destroy()
        except Exception:
            pass


class MainWindow(ctk.CTk):
    """Panel de Control Principal estilo Corporativo NovaSource."""

    def __init__(self, core_app):
        super().__init__()
        self.core_app = core_app
        self.title("NovaSource | Centro de Operaciones")
        self.geometry("1200x780")
        self.minsize(980, 650)
        self.configure(fg_color="#F4F7FB")
        aplicar_icono_ventana(self)
        self.protocol("WM_DELETE_WINDOW", self._cerrar_aplicacion)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._crear_encabezado()
        self._crear_navegacion()

        self.contenido = ctk.CTkFrame(self, fg_color="#F4F7FB", corner_radius=0)
        self.contenido.grid(row=1, column=1, sticky="nsew")
        self.contenido.grid_rowconfigure(0, weight=1)
        self.contenido.grid_columnconfigure(0, weight=1)

        self.page_reports = ctk.CTkFrame(self.contenido, fg_color="transparent")
        self.page_cctv = ctk.CTkFrame(self.contenido, fg_color="transparent")
        for page in (self.page_reports, self.page_cctv):
            page.grid(row=0, column=0, sticky="nsew")

        self._crear_panel_control()
        self._crear_panel_resumen_y_logs()
        from .whatsapp_tab import WhatsAppTab
        self.whatsapp_tab = WhatsAppTab(self.page_cctv)
        self.whatsapp_tab.pack(fill="both", expand=True, padx=12, pady=12)
        self._mostrar_pagina("reportes")

    def _crear_navegacion(self):
        nav = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0,
                           border_width=1, border_color="#E4EAF1", width=224)
        nav.grid(row=1, column=0, sticky="nsew")
        nav.grid_propagate(False)
        ctk.CTkLabel(nav, text="ESPACIO DE TRABAJO", text_color="#8A98AA",
                     font=ctk.CTkFont(size=10, weight="bold")).pack(
                         anchor="w", padx=20, pady=(30, 12))
        self.nav_reportes = ctk.CTkButton(
            nav, text="▦   Reportes semanales", anchor="w", height=44,
            corner_radius=9, font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._mostrar_pagina("reportes"))
        self.nav_reportes.pack(fill="x", padx=12, pady=4)
        self.nav_cctv = ctk.CTkButton(
            nav, text="▣   CCTV · WhatsApp", anchor="w", height=44,
            corner_radius=9, font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._mostrar_pagina("cctv"))
        self.nav_cctv.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(nav, text="OPERACIONES CHILE", text_color="#94A3B8",
                     font=ctk.CTkFont(size=10, weight="bold")).pack(
                         side="bottom", anchor="w", padx=20, pady=22)

    def _mostrar_pagina(self, pagina):
        active, muted = "#E7F0FF", "#FFFFFF"
        for btn, selected in ((self.nav_reportes, pagina == "reportes"),
                              (self.nav_cctv, pagina == "cctv")):
            btn.configure(fg_color=active if selected else muted,
                          hover_color="#DCEAFF" if selected else "#F2F6FA",
                          text_color="#1456A0" if selected else "#52647A")
        (self.page_reports if pagina == "reportes" else self.page_cctv).tkraise()
        self.lbl_contexto.configure(text="Reportes semanales" if pagina == "reportes"
                                   else "Monitoreo CCTV · WhatsApp")

    def _cerrar_aplicacion(self):
        try:
            self.withdraw()
            self.quit()
            self.destroy()
        except Exception:
            pass

    def _crear_encabezado(self):
        header = ctk.CTkFrame(self, height=76, corner_radius=0,
                              fg_color="#FFFFFF", border_width=1,
                              border_color="#E4EAF1")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)
        logo_path = resource_path("assets/novasource_logo.png")
        if logo_path.is_file():
            try:
                im = Image.open(logo_path).convert("RGBA")
                self._header_logo = ctk.CTkImage(
                    light_image=im, dark_image=im, size=(52, 52)
                )
                ctk.CTkLabel(header, image=self._header_logo, text="",
                             width=58, height=58).pack(
                    side="left", padx=(24, 16), pady=8
                )
            except Exception as exc:
                print(f"No se pudo mostrar el logo: {exc}")
        text_frame = ctk.CTkFrame(header, fg_color="transparent")
        text_frame.pack(side="left", fill="y", pady=12)
        ctk.CTkLabel(text_frame, text="NovaSource | Centro de Operaciones",
                     text_color="#172B4D",
                     font=ctk.CTkFont(size=19, weight="bold")
                     ).pack(anchor="w")
        self.lbl_contexto = ctk.CTkLabel(text_frame, text="Reportes semanales",
                     text_color="#718096", font=ctk.CTkFont(size=11))
        self.lbl_contexto.pack(anchor="w")
        ctk.CTkButton(header, text="Ver Excel Maestro", width=154, height=37,
                      corner_radius=8, fg_color="#EDF4FF", hover_color="#DCEAFF",
                      text_color="#1456A0", font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._ver_previsualizacion_maestro).pack(
                          side="right", padx=24)

    def _ver_previsualizacion_maestro(self):
        """Previsualización limpia y estilizada de la última hoja del Excel Maestro sin etiquetas Unnamed."""
        ruta_maestro = None

        if hasattr(self.core_app, "config_manager"):
            ruta_maestro = getattr(self.core_app.config_manager, "ruta_maestro", None)
        elif hasattr(self.core_app, "config"):
            cfg = self.core_app.config
            ruta_maestro = getattr(cfg, "ruta_maestro", None) or (cfg.get("ruta_maestro") if isinstance(cfg, dict) else None)
        elif hasattr(self.core_app, "ruta_maestro"):
            ruta_maestro = self.core_app.ruta_maestro

        if not ruta_maestro or not os.path.exists(str(ruta_maestro)):
            messagebox.showwarning("Atención", "No se encontró una ruta de Excel Maestro configurada o el archivo no existe.")
            return

        try:
            excel_file = pd.ExcelFile(ruta_maestro)
            hojas = excel_file.sheet_names

            if not hojas:
                messagebox.showinfo("Información", "El archivo Excel Maestro no contiene hojas de trabajo.")
                return

            ultima_hoja = hojas[-1]

            # Leemos sin header estricto para procesar filas combinadas
            df_raw = pd.read_excel(excel_file, sheet_name=ultima_hoja, header=None, nrows=25)

            if df_raw.empty:
                messagebox.showinfo("Información", f"La última hoja ('{ultima_hoja}') está vacía.")
                return

            # Limpieza y renombramiento de etiquetas Unnamed
            df = df_raw.copy()
            
            # Reemplazar encabezados que contengan 'Unnamed' por nombres limpios o espacios
            nuevas_columnas = []
            for i, col in enumerate(df.columns):
                val = str(col)
                if "Unnamed:" in val or val.strip() == "":
                    nuevas_columnas.append(f"Columna {i+1}")
                else:
                    nuevas_columnas.append(val)
            df.columns = nuevas_columnas

            # Ventana secundaria estilo Dashboard
            top = ctk.CTkToplevel(self)
            top.title(f"Vista Previa Maestro - [{ultima_hoja}]")
            top.geometry("920x520")
            top.grab_set()
            top.configure(fg_color="#F8FAFC")

            aplicar_icono_ventana(top)

            # Banner Informativo Superior
            info_frame = ctk.CTkFrame(top, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E2E8F0")
            info_frame.pack(fill="x", padx=20, pady=(15, 12))

            lbl_hoja = ctk.CTkLabel(
                info_frame,
                text=f"📊  ÚLTIMA HOJA: {ultima_hoja}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#0D47A1"
            )
            lbl_hoja.pack(side="left", padx=16, pady=10)

            lbl_archivo = ctk.CTkLabel(
                info_frame,
                text=f"📁 {os.path.basename(str(ruta_maestro))}",
                font=ctk.CTkFont(size=11),
                text_color="#64748B"
            )
            lbl_archivo.pack(side="right", padx=16, pady=10)

            # Contenedor de la Tabla
            frame_tabla = ctk.CTkFrame(top, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E2E8F0")
            frame_tabla.pack(fill="both", expand=True, padx=20, pady=(0, 20))

            # Estilo moderno para el Treeview
            style = ttk.Style()
            style.theme_use("clam")
            
            font_family = 'Segoe UI' if sys.platform.startswith('win') else 'Calibri'
            
            style.configure(
                "Custom.Treeview",
                background="#FFFFFF",
                fieldbackground="#FFFFFF",
                foreground="#1E293B",
                rowheight=28,
                bordercolor="#E2E8F0",
                borderwidth=0,
                font=(font_family, 10)
            )
            style.configure(
                "Custom.Treeview.Heading",
                background="#1E293B",
                foreground="#FFFFFF",
                relief="flat",
                font=(font_family, 10, 'bold')
            )
            style.map("Custom.Treeview.Heading", background=[('active', '#334155')])

            cols = list(df.columns)
            tree = ttk.Treeview(frame_tabla, style="Custom.Treeview", columns=cols, show='headings', selectmode='browse')

            # Barras de desplazamiento
            scroll_y = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
            scroll_x = ttk.Scrollbar(frame_tabla, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

            scroll_y.pack(side="right", fill="y")
            scroll_x.pack(side="bottom", fill="x")
            tree.pack(fill="both", expand=True, padx=2, pady=2)

            for c in cols:
                tree.heading(c, text=str(c))
                tree.column(c, width=150, anchor="center")

            # Alternancia de colores en filas (Zebra Striping)
            tree.tag_configure('par', background='#F8FAFC')
            tree.tag_configure('impar', background='#FFFFFF')

            for idx, row in df.iterrows():
                valores = [str(val) if (pd.notna(val) and str(val) != "nan") else "" for val in row]
                tag = 'par' if idx % 2 == 0 else 'impar'
                tree.insert("", "end", values=valores, tags=(tag,))

        except Exception as e:
            messagebox.showerror("Error de Lectura", f"No se pudo cargar la vista previa:\n\n{str(e)}")

    def _crear_panel_control(self):
        card = ctk.CTkFrame(self.page_reports, fg_color="#FFFFFF", corner_radius=14,
                            border_width=1, border_color="#E4EAF1")
        card.pack(fill="x", padx=20, pady=(22, 14))
        ctk.CTkLabel(card, text="Importar reporte semanal",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color="#172B4D").pack(anchor="w", padx=22, pady=(19, 2))
        ctk.CTkLabel(card, text="Selecciona el archivo Excel que deseas procesar y consolidar.",
                     font=ctk.CTkFont(size=12), text_color="#718096").pack(
                         anchor="w", padx=22, pady=(0, 15))
        line = ctk.CTkFrame(card, fg_color="transparent")
        line.pack(fill="x", padx=22, pady=(0, 22))
        self.entry_reporte = ctk.CTkEntry(
            line, placeholder_text="Ruta del reporte semanal (.xlsx o .xlsm)",
            height=42, corner_radius=8, fg_color="#F8FAFD",
            border_color="#D8E2EF", text_color="#172B4D")
        self.entry_reporte.pack(side="left", fill="x", expand=True, padx=(0, 9))
        ctk.CTkButton(line, text="Examinar", width=100, height=42,
                      fg_color="#EAF1F9", hover_color="#DCE7F4",
                      text_color="#24527A", command=self._seleccionar_reporte).pack(
                          side="left", padx=(0, 9))
        self.btn_procesar = ctk.CTkButton(
            line, text="Procesar reporte", width=156, height=42,
            fg_color="#1565B8", hover_color="#0F4F95", corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._ejecutar_procesamiento)
        self.btn_procesar.pack(side="left")

    def _crear_panel_resumen_y_logs(self):
        container = ctk.CTkFrame(self.page_reports, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)
        cards = ctk.CTkFrame(container, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        cards.grid_columnconfigure((0, 1, 2), weight=1)
        metrics = (
            ("TOTAL LEÍDOS", "lbl_num_total", "#172B4D"),
            ("AGREGADOS / ACTUALIZADOS", "lbl_num_exito", "#15803D"),
            ("OMITIDOS / SIN CAMBIOS", "lbl_num_omitidos", "#C24135"),
        )
        for index, (label, attr, color) in enumerate(metrics):
            card = ctk.CTkFrame(cards, fg_color="#FFFFFF", corner_radius=12,
                                border_width=1, border_color="#E4EAF1")
            card.grid(row=0, column=index, sticky="ew",
                      padx=(0, 8) if index == 0 else ((8, 0) if index == 2 else 8))
            ctk.CTkLabel(card, text=label, text_color="#718096",
                         font=ctk.CTkFont(size=10, weight="bold")).pack(
                             anchor="w", padx=19, pady=(15, 2))
            value = ctk.CTkLabel(card, text="0", text_color=color,
                                 font=ctk.CTkFont(size=29, weight="bold"))
            value.pack(anchor="w", padx=19, pady=(0, 13))
            setattr(self, attr, value)
        logs_card = ctk.CTkFrame(container, fg_color="#FFFFFF", corner_radius=12,
                                 border_width=1, border_color="#E4EAF1")
        logs_card.grid(row=1, column=0, sticky="nsew")
        head = ctk.CTkFrame(logs_card, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 9))
        ctk.CTkLabel(head, text="Registro de actividad",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#172B4D").pack(side="left")
        ctk.CTkButton(head, text="Limpiar", width=75, height=28,
                      fg_color="#F1F5F9", hover_color="#E2E8F0",
                      text_color="#52647A", command=self._limpiar_logs).pack(side="right")
        self.txt_logs = ctk.CTkTextbox(
            logs_card, fg_color="#F8FAFD", text_color="#334155",
            font=ctk.CTkFont(family="Consolas", size=11),
            border_width=1, border_color="#E4EAF1", corner_radius=9,
            wrap="word", state="disabled")
        self.txt_logs.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.log("SISTEMA LISTO. Selecciona un archivo semanal para iniciar auditoría.")

    def _limpiar_logs(self):
        self.txt_logs.configure(state="normal")
        self.txt_logs.delete("1.0", "end")
        self.txt_logs.configure(state="disabled")

    def log(self, mensaje: str):
        """Escribe un mensaje en la consola de la interfaz de forma segura."""
        self.txt_logs.configure(state="normal")
        self.txt_logs.insert("end", f"> {mensaje}\n")
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def _seleccionar_reporte(self):
        filename = filedialog.askopenfilename(
            title="Seleccionar Reporte Semanal",
            filetypes=[("Archivos de Excel", "*.xlsx *.xlsm")]
        )
        if filename:
            self.entry_reporte.delete(0, "end")
            self.entry_reporte.insert(0, filename)

    def _ejecutar_procesamiento(self):
        ruta = self.entry_reporte.get().strip()
        if not ruta:
            messagebox.showwarning("Atención", "Selecciona un archivo de reporte semanal primero.")
            return

        self.btn_procesar.configure(state="disabled")

        self.lbl_num_total.configure(text="0")
        self.lbl_num_exito.configure(text="0")
        self.lbl_num_omitidos.configure(text="0")

        try:
            resumen = self.core_app.run(self.log, ruta)

            if isinstance(resumen, dict):
                total = resumen.get("total", 0)
                agregados = resumen.get("agregados", 0)
                omitidos = resumen.get("omitidos", 0)
            else:
                total = resumen if isinstance(resumen, int) else 0
                agregados = total
                omitidos = 0

            self.lbl_num_total.configure(text=str(total))
            self.lbl_num_exito.configure(text=str(agregados))
            self.lbl_num_omitidos.configure(text=str(omitidos))

            messagebox.showinfo(
                "Proceso Finalizado",
                f"Reporte procesado exitosamente.\n\nTotal procesados: {total}\nNuevos/Actualizados: {agregados}\nOmitidos/Sin cambios: {omitidos}"
            )

        except Exception as e:
            error_detallado = traceback.format_exc()
            print("=== ERROR DETALLADO ===")
            print(error_detallado)

            self.log(f"ERROR CRÍTICO: {str(e)}")
            messagebox.showerror("Error de Procesamiento", f"Ocurrió un error al procesar:\n\n{str(e)}")
        finally:
            self.btn_procesar.configure(state="normal")