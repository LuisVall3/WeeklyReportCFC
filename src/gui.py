"""
gui.py

Interfaz gráfica de usuario para NovaSource Power Services.
Contiene la ventana principal (MainWindow) y el modal de configuración (SetupDialog).
"""

import threading
import traceback
import customtkinter as ctk
from tkinter import messagebox, filedialog


# ==========================================
# PALETA DE COLORES (NovaSource Power Brand)
# ==========================================
COLOR_BG_DARK = "#0F172A"       # Azul pizarra muy oscuro / Fondo principal
COLOR_CARD_BG = "#1E293B"       # Contenedores y tarjetas
COLOR_ACCENT_GREEN = "#10B981"  # Verde energía / Éxito
COLOR_ACCENT_BLUE = "#0284C7"   # Azul corporativo
COLOR_TEXT_MAIN = "#F8FAFC"     # Texto principal
COLOR_TEXT_MUTED = "#94A3B8"    # Texto secundario
COLOR_ERROR = "#EF4444"         # Rojo error
COLOR_WARNING = "#F59E0B"       # Amarillo procesamiento


class MainWindow(ctk.CTk):

    def __init__(self, app):
        super().__init__()

        self.app = app

        # ==========================
        # CONFIGURACIÓN DE VENTANA
        # ==========================
        self.title("NovaSource Power | CCTV Weekly Report CFC")
        self.geometry("900x650")
        self.minsize(800, 580)

        ctk.set_appearance_mode("Dark")
        self.configure(fg_color=COLOR_BG_DARK)

        self._crear_interfaz()

    def _crear_interfaz(self):
        # Grid principal (1 columna, 4 filas)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ==========================
        # 1. ENCABEZADO / BRANDING
        # ==========================
        self.header_frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD_BG,
            corner_radius=12
        )
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        self.header_frame.grid_columnconfigure(0, weight=1)

        # Contenedor de títulos
        self.title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.title_box.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self.brand_label = ctk.CTkLabel(
            self.title_box,
            text="NOVASOURCE POWER SERVICES",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_ACCENT_GREEN
        )
        self.brand_label.pack(anchor="w")

        self.titulo = ctk.CTkLabel(
            self.title_box,
            text="CCTV Weekly Report CFC",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.titulo.pack(anchor="w")

        self.subtitulo = ctk.CTkLabel(
            self.title_box,
            text="Weekly CCTV Alarms & Operator Log Processing System",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED
        )
        self.subtitulo.pack(anchor="w")

        # ==========================
        # 2. STATUS & CONTROLES
        # ==========================
        self.action_frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD_BG,
            corner_radius=12
        )
        self.action_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.action_frame.grid_columnconfigure(0, weight=1)

        # Indicador de estado
        self.status_box = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.status_box.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self.lbl_estado_tag = ctk.CTkLabel(
            self.status_box,
            text="ESTADO DEL SISTEMA",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_estado_tag.pack(anchor="w")

        self.estado = ctk.CTkLabel(
            self.status_box,
            text="● SISTEMA LISTO",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLOR_ACCENT_GREEN
        )
        self.estado.pack(anchor="w", pady=(2, 0))

        # Botón de Importación
        self.boton_importar = ctk.CTkButton(
            self.action_frame,
            text="⚡ IMPORTAR REPORTE",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_ACCENT_GREEN,
            hover_color="#059669",
            text_color="#022C22",
            height=45,
            corner_radius=8,
            command=self.iniciar_importacion_thread
        )
        self.boton_importar.grid(row=0, column=1, padx=20, pady=15, sticky="e")

        # ==========================
        # 3. CONSOLA / LOGS
        # ==========================
        self.log_header = ctk.CTkFrame(self, fg_color="transparent")
        self.log_header.grid(row=2, column=0, padx=25, pady=(10, 5), sticky="ew")

        self.label_log = ctk.CTkLabel(
            self.log_header,
            text="Registro de Procesamiento (Logs)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.label_log.pack(side="left")

        # Caja de Texto tipo Terminal moderna
        self.log = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0B132B",
            text_color="#E2E8F0",
            border_width=1,
            border_color="#334155",
            corner_radius=10
        )
        self.log.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Mensajes de inicio
        self.escribir("SYSTEM: Conexión con NovaSource Power Services establecida.")
        self.escribir("READY: Esperando reporte semanal CCTV para importar registros...")

    # ==========================
    # LÓGICA Y MÉTODOS
    # ==========================

    def escribir(self, texto: str):
        """Escribe una línea en la consola de logs con auto scroll."""
        self.log.insert("end", texto + "\n")
        self.log.see("end")

    def iniciar_importacion_thread(self):
        """Abre el explorador de archivos y, si se selecciona uno, inicia la importación."""
        archivo_seleccionado = filedialog.askopenfilename(
            title="Seleccionar reporte CCTV Excel para importar",
            initialdir=str(self.app.config.ruta_descargas),
            filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")]
        )

        if not archivo_seleccionado:
            self.escribir("CANCELADO: No se seleccionó ningún archivo.")
            return

        self.boton_importar.configure(state="disabled", fg_color="#334155")
        self.estado.configure(text="● PROCESANDO...", text_color=COLOR_WARNING)

        self.log.delete("1.0", "end")
        self.escribir(f"STATUS: Archivo seleccionado -> {archivo_seleccionado}")

        thread = threading.Thread(
            target=self._ejecutar_proceso,
            args=(archivo_seleccionado,),
            daemon=True
        )
        thread.start()

    def _ejecutar_proceso(self, ruta_archivo):
        """Tarea pesada en segundo plano."""
        try:
            self.app.run(self.escribir, ruta_archivo=ruta_archivo)
            self.after(0, self._al_finalizar_exito)

        except Exception as e:
            error_detallado = traceback.format_exc()
            self.after(0, lambda err=error_detallado: self._al_finalizar_error(err))

    def _al_finalizar_exito(self):
        self.estado.configure(text="● IMPORTACIÓN COMPLETADA", text_color=COLOR_ACCENT_GREEN)
        self.escribir("\nSUCCESS: Proceso finalizado correctamente sin errores.")
        self.boton_importar.configure(state="normal", fg_color=COLOR_ACCENT_GREEN)

        messagebox.showinfo(
            "CCTV Weekly Report CFC",
            "El reporte semanal de alarmas CCTV se ha procesado con éxito en el Excel Maestro."
        )

    def _al_finalizar_error(self, error_msg: str):
        self.estado.configure(text="● ERROR EN PROCESO", text_color=COLOR_ERROR)
        self.escribir(f"\nCRITICAL ERROR:\n{error_msg}")
        self.boton_importar.configure(state="normal", fg_color=COLOR_ACCENT_GREEN)

        messagebox.showerror(
            "Error de Importación",
            f"Ocurrió un error durante la ejecución:\n\n{error_msg}"
        )


# ==========================================
# DIÁLOGO DE CONFIGURACIÓN INICIAL
# ==========================================
class SetupDialog(ctk.CTk):

    def __init__(self, config_manager):
        super().__init__()

        self.config_manager = config_manager

        self.title("CCTV Weekly Report CFC | Configuración Inicial")
        self.geometry("550x380")
        self.resizable(False, False)

        ctk.set_appearance_mode("Dark")
        self.configure(fg_color=COLOR_BG_DARK)

        rutas = self.config_manager.config.get("rutas", {})
        self.ruta_maestro = ctk.StringVar(value=rutas.get("maestro", ""))
        self.ruta_logs = ctk.StringVar(value=rutas.get("logs", ""))

        self._crear_widgets()

    def _crear_widgets(self):
        lbl_titulo = ctk.CTkLabel(
            self,
            text="CONFIGURACIÓN DE RUTAS",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        lbl_titulo.pack(pady=(20, 5))

        lbl_sub = ctk.CTkLabel(
            self,
            text="Selecciona dónde se encuentran los archivos maestros y logs",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        lbl_sub.pack(pady=(0, 20))

        # --- ARCHIVO MAESTRO ---
        lbl_m = ctk.CTkLabel(
            self,
            text="Archivo Excel Maestro (.xlsx):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_ACCENT_GREEN
        )
        lbl_m.pack(anchor="w", padx=30)

        frame_m = ctk.CTkFrame(self, fg_color="transparent")
        frame_m.pack(fill="x", padx=30, pady=(5, 15))

        entry_m = ctk.CTkEntry(frame_m, textvariable=self.ruta_maestro, placeholder_text="Ruta del Excel Maestro...")
        entry_m.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_m = ctk.CTkButton(frame_m, text="Buscar", width=80, fg_color=COLOR_ACCENT_BLUE, command=self._seleccionar_maestro)
        btn_m.pack(side="right")

        # --- CARPETA LOGS ---
        lbl_l = ctk.CTkLabel(
            self,
            text="Carpeta de Registros (Logs):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_ACCENT_GREEN
        )
        lbl_l.pack(anchor="w", padx=30)

        frame_l = ctk.CTkFrame(self, fg_color="transparent")
        frame_l.pack(fill="x", padx=30, pady=(5, 20))

        entry_l = ctk.CTkEntry(frame_l, textvariable=self.ruta_logs, placeholder_text="Carpeta donde guardar logs...")
        entry_l.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_l = ctk.CTkButton(frame_l, text="Buscar", width=80, fg_color=COLOR_ACCENT_BLUE, command=self._seleccionar_logs)
        btn_l.pack(side="right")

        # --- BOTÓN GUARDAR ---
        btn_guardar = ctk.CTkButton(
            self,
            text="GUARDAR Y CONTINUAR",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_ACCENT_GREEN,
            hover_color="#059669",
            text_color="#022C22",
            height=40,
            command=self._guardar
        )
        btn_guardar.pack(pady=10)

    def _seleccionar_maestro(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Excel Maestro",
            filetypes=[("Archivos Excel", "*.xlsx")]
        )
        if file_path:
            self.ruta_maestro.set(file_path)

    def _seleccionar_logs(self):
        dir_path = filedialog.askdirectory(title="Seleccionar Carpeta de Logs")
        if dir_path:
            self.ruta_logs.set(dir_path)

    def _guardar(self):
        if not self.ruta_maestro.get() or not self.ruta_logs.get():
            messagebox.showwarning("Atención", "Por favor define ambas rutas antes de continuar.")
            return

        self.config_manager.guardar_rutas(self.ruta_maestro.get(), self.ruta_logs.get())
        self.destroy()