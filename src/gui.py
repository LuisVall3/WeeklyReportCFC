import os
import sys
import traceback
from pathlib import Path
from typing import Optional
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageEnhance

# Configuración de tema Corporativo / Claro
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


def aplicar_icono_ventana(window):
    """Aplica el ícono corporativo desde assets/ según el sistema operativo (Windows/macOS)."""
    base_dir = Path(__file__).resolve().parent.parent
    ruta_png = base_dir / "assets" / "novasource_logo.png"
    ruta_ico = base_dir / "assets" / "favicon.ico"

    if sys.platform == "darwin":
        def _cargar_mac():
            if ruta_png.exists():
                try:
                    img_pil = Image.open(ruta_png)
                    photo = ImageTk.PhotoImage(img_pil)
                    window.tk.call('wm', 'iconphoto', window._w, photo)
                    window._icon_photo = photo
                except Exception as e:
                    print(f"Error cargando icono en macOS: {e}")

        window.after(200, _cargar_mac)

    elif sys.platform.startswith("win"):
        try:
            import ctypes
            myappid = "novasource.weeklyreport.cfc.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        def _cargar_win():
            if ruta_ico.exists():
                try:
                    window.iconbitmap(str(ruta_ico))
                except Exception:
                    pass

        window.after(200, _cargar_win)


def cargar_logo_fondo(ancho: int = 240, opacidad: float = 0.05) -> Optional[ctk.CTkImage]:
    """Carga el logo y le aplica una opacidad muy suave (marca de agua)."""
    base_dir = Path(__file__).resolve().parent.parent
    ruta_png = base_dir / "assets" / "novasource_logo.png"

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

        self.title("Gestión de Reportes Semanales - NovaSource")
        self.geometry("950x680")
        self.minsize(850, 600)
        self.configure(fg_color="#F4F6F8")

        aplicar_icono_ventana(self)
        self.protocol("WM_DELETE_WINDOW", self._cerrar_aplicacion)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._crear_encabezado()
        self._crear_panel_control()
        self._crear_panel_resumen_y_logs()

    def _cerrar_aplicacion(self):
        try:
            self.withdraw()
            self.quit()
            self.destroy()
        except Exception:
            pass

    def _crear_encabezado(self):
        """Header limpio con logo compacto, título y botón para ver el maestro."""
        header_frame = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color="#FFFFFF",
            height=55,
            border_width=1,
            border_color="#E0E0E0"
        )
        header_frame.grid(row=0, column=0, sticky="ew")

        base_dir = Path(__file__).resolve().parent.parent
        ruta_png = base_dir / "assets" / "novasource_logo.png"
        
        if ruta_png.exists():
            try:
                img = Image.open(ruta_png)
                ancho_deseado = 45
                ratio = ancho_deseado / float(img.size[0])
                alto = int(float(img.size[1]) * ratio)
                img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(ancho_deseado, alto))
                
                lbl_logo_header = ctk.CTkLabel(header_frame, image=img_ctk, text="")
                lbl_logo_header.pack(side="left", padx=(20, 8), pady=8)
            except Exception:
                pass

        lbl_title = ctk.CTkLabel(
            header_frame,
            text="Consola de Monitoreo & Reportes",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#0D47A1"
        )
        lbl_title.pack(side="left", padx=5, pady=14)

        btn_ver_maestro = ctk.CTkButton(
            header_frame,
            text="👁️ Ver Maestro",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            width=110,
            fg_color="#EDF2F7",
            hover_color="#E2E8F0",
            text_color="#2D3748",
            border_width=1,
            border_color="#CBD5E1",
            command=self._ver_previsualizacion_maestro
        )
        btn_ver_maestro.pack(side="right", padx=20, pady=11)

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
        """Panel de selección de archivo e inicio de procesamiento."""
        control_frame = ctk.CTkFrame(
            self,
            corner_radius=8,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E0E0E0"
        )
        control_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(20, 10))

        lbl_section = ctk.CTkLabel(
            control_frame,
            text="Carga de Reporte Semanal",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1A252C"
        )
        lbl_section.pack(anchor="w", padx=20, pady=(12, 6))

        file_select_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        file_select_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.entry_reporte = ctk.CTkEntry(
            file_select_frame,
            placeholder_text="Seleccionar archivo semanal a procesar (.xlsx)...",
            fg_color="#F8F9FA",
            border_color="#CED4DA",
            text_color="#1A252C",
            height=36
        )
        self.entry_reporte.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_browse = ctk.CTkButton(
            file_select_frame,
            text="Examinar...",
            width=100,
            height=36,
            fg_color="#E2E8F0",
            hover_color="#CBD5E1",
            text_color="#1E293B",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._seleccionar_reporte
        )
        btn_browse.pack(side="left", padx=(0, 10))

        self.btn_procesar = ctk.CTkButton(
            file_select_frame,
            text="Procesar Reporte",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            fg_color="#0D47A1",
            hover_color="#0A3880",
            text_color="#FFFFFF",
            command=self._ejecutar_procesamiento
        )
        self.btn_procesar.pack(side="right")

    def _crear_panel_resumen_y_logs(self):
        """Métricas rápidas y consola de auditoría."""
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)

        # --- PANEL DE MÉTRICAS / TARJETAS ---
        cards_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Tarjeta 1
        self.card_total = ctk.CTkFrame(cards_frame, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E0E0E0")
        self.card_total.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        ctk.CTkLabel(self.card_total, text="TOTAL LEÍDOS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#5F6D7A").pack(pady=(10, 0))
        self.lbl_num_total = ctk.CTkLabel(self.card_total, text="0", font=ctk.CTkFont(size=22, weight="bold"), text_color="#1A252C")
        self.lbl_num_total.pack(pady=(0, 10))

        # Tarjeta 2
        self.card_exito = ctk.CTkFrame(cards_frame, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E0E0E0")
        self.card_exito.grid(row=0, column=1, padx=6, sticky="ew")
        ctk.CTkLabel(self.card_exito, text="AGREGADOS / ACTUALIZADOS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#2E7D32").pack(pady=(10, 0))
        self.lbl_num_exito = ctk.CTkLabel(self.card_exito, text="0", font=ctk.CTkFont(size=22, weight="bold"), text_color="#2E7D32")
        self.lbl_num_exito.pack(pady=(0, 10))

        # Tarjeta 3
        self.card_omitidos = ctk.CTkFrame(cards_frame, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E0E0E0")
        self.card_omitidos.grid(row=0, column=2, padx=(6, 0), sticky="ew")
        ctk.CTkLabel(self.card_omitidos, text="OMITIDOS / SIN CAMBIOS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#C62828").pack(pady=(10, 0))
        self.lbl_num_omitidos = ctk.CTkLabel(self.card_omitidos, text="0", font=ctk.CTkFont(size=22, weight="bold"), text_color="#C62828")
        self.lbl_num_omitidos.pack(pady=(0, 10))

        # --- CONSOLA DE AUDITORÍA / LOGS ---
        log_frame = ctk.CTkFrame(
            main_container,
            fg_color="#FFFFFF",
            corner_radius=8,
            border_width=1,
            border_color="#E0E0E0"
        )
        log_frame.grid(row=1, column=0, sticky="nsew")

        lbl_console = ctk.CTkLabel(
            log_frame,
            text="Registro de Auditoría y Eventos",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#5F6D7A"
        )
        lbl_console.pack(anchor="w", padx=16, pady=(10, 6))

        logo_watermark = cargar_logo_fondo(ancho=260, opacidad=0.06)
        if logo_watermark:
            lbl_watermark = ctk.CTkLabel(log_frame, image=logo_watermark, text="", fg_color="transparent")
            lbl_watermark.place(relx=0.5, rely=0.55, anchor="center")
            lbl_watermark.lower()

        self.txt_logs = ctk.CTkTextbox(
            log_frame,
            fg_color="transparent",
            text_color="#24292E",
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            border_width=1,
            border_color="#E2E8F0",
            state="disabled"
        )
        self.txt_logs.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.log("SISTEMA LISTO. Selecciona un archivo semanal para iniciar auditoría.")

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