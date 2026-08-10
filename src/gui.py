"""
src/gui.py

Interfaz Gráfica (Tkinter / CustomTkinter) con diseño tipo Centro de Control CCTV.
Permite configurar rutas, procesar reportes semanales y ver métricas/logs detallados.
"""

import os
import sys
import traceback
from pathlib import Path
from typing import Optional
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Configuración de tema tipo Dashboard CCTV
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


from PIL import Image, ImageTk

def aplicar_icono_ventana(window):
    """Aplica el ícono corporativo desde assets/ según el sistema operativo (Windows/macOS)."""
    base_dir = Path(__file__).resolve().parent.parent
    ruta_png = base_dir / "assets" / "novasource_logo.png"
    ruta_ico = base_dir / "assets" / "favicon.ico"

    # --- CONFIGURACIÓN PARA MACOS ---
    if sys.platform == "darwin":
        def _cargar_mac():
            if ruta_png.exists():
                try:
                    # Asignar imagen al Dock de macOS mediante la API nativa de Tkinter
                    img_pil = Image.open(ruta_png)
                    photo = ImageTk.PhotoImage(img_pil)
                    window.tk.call('wm', 'iconphoto', window._w, photo)
                    window._icon_photo = photo
                except Exception as e:
                    print(f"Error cargando icono en macOS: {e}")

        window.after(200, _cargar_mac)

    # --- CONFIGURACIÓN PARA WINDOWS ---
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

class SetupDialog(ctk.CTk):
    """Ventana inicial de configuración de rutas."""

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager

        self.title("CCTV Control Center - Configuración Inicial")
        self.geometry("600x420")
        self.resizable(False, False)

        # Aplicar el ícono corporativo
        aplicar_icono_ventana(self)

        # Capturar el botón de cerrar la ventana (X)
        self.protocol("WM_DELETE_WINDOW", self._cerrar_limpio)

        # Contenedor principal
        self.frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#1A1C1E")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Encabezado
        self.lbl_title = ctk.CTkLabel(
            self.frame,
            text="🎛️ CONFIGURACIÓN DE RUTAS DEL SISTEMA",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#00D2FF"
        )
        self.lbl_title.pack(pady=(20, 10))

        self.lbl_subtitle = ctk.CTkLabel(
            self.frame,
            text="Selecciona el archivo Excel Maestro para habilitar la consola de monitoreo.",
            font=ctk.CTkFont(size=12),
            text_color="#A0AAB0"
        )
        self.lbl_subtitle.pack(pady=(0, 20))

        # Input: Excel Maestro
        self.lbl_maestro = ctk.CTkLabel(
            self.frame, text="Ruta Excel Maestro (.xlsx):", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_maestro.pack(anchor="w", padx=30, pady=(5, 2))

        self.frame_maestro = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.frame_maestro.pack(fill="x", padx=30, pady=(0, 15))

        ruta_inicial_maestro = self.config_manager.ruta_maestro
        self.entry_maestro = ctk.CTkEntry(
            self.frame_maestro,
            placeholder_text="Selecciona archivo Excel Maestro...",
            fg_color="#26292B",
            border_color="#3A3D40"
        )
        self.entry_maestro.pack(side="left", fill="x", expand=True, padx=(0, 10))
        if ruta_inicial_maestro:
            self.entry_maestro.insert(0, ruta_inicial_maestro)

        self.btn_browse_maestro = ctk.CTkButton(
            self.frame_maestro,
            text="Buscar",
            width=90,
            fg_color="#007ACC",
            hover_color="#005999",
            command=self._buscar_maestro
        )
        self.btn_browse_maestro.pack(side="right")

        # Botón Guardar
        self.btn_guardar = ctk.CTkButton(
            self.frame,
            text="Guardar y Entrar al Panel",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00B0FF",
            hover_color="#0088CC",
            text_color="#000000",
            command=self._guardar
        )
        self.btn_guardar.pack(fill="x", padx=30, pady=(30, 20))

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
        """Cierre controlado para evitar advertencias de CustomTkinter."""
        try:
            self.withdraw()
            self.quit()
            self.destroy()
        except Exception:
            pass


class MainWindow(ctk.CTk):
    """Panel de Control Principal estilo CCTV Operator."""

    def __init__(self, core_app):
        super().__init__()
        self.core_app = core_app

        self.title("Reporte Semanal CFC - NovaSource")
        self.geometry("900x650")
        self.minsize(800, 550)

        # Aplicar el ícono corporativo
        aplicar_icono_ventana(self)

        # Capturar el evento de cierre de ventana (X)
        self.protocol("WM_DELETE_WINDOW", self._cerrar_aplicacion)

        # Configurar Grid principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._crear_encabezado()
        self._crear_panel_control()
        self._crear_panel_resumen_y_logs()

    def _cerrar_aplicacion(self):
        """Maneja el cierre limpio de la ventana sin advertencias."""
        try:
            self.withdraw()
            self.quit()
            self.destroy()
        except Exception:
            pass

    def _crear_encabezado(self):
        """Header estilo consola de monitoreo."""
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#111315", height=60)
        header_frame.grid(row=0, column=0, sticky="ew")

        lbl_status_icon = ctk.CTkLabel(
            header_frame,
            text="🔴 MONITOREO ACTIVO",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00FF66"
        )
        lbl_status_icon.pack(side="left", padx=20, pady=15)

        lbl_title = ctk.CTkLabel(
            header_frame,
            text="SISTEMA DE GESTIÓN DE REPORTES CCTV - NOVASOURCE",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(side="right", padx=20)

    def _crear_panel_control(self):
        """Panel de selección de archivo e inicio de procesamiento."""
        control_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1A1C1E")
        control_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=15)

        lbl_section = ctk.CTkLabel(
            control_frame,
            text="📁 CARGA DE REPORTE SEMANAL",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00D2FF"
        )
        lbl_section.pack(anchor="w", padx=15, pady=(10, 5))

        file_select_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        file_select_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.entry_reporte = ctk.CTkEntry(
            file_select_frame,
            placeholder_text="Seleccionar archivo semanal a procesar...",
            fg_color="#26292B",
            border_color="#3A3D40"
        )
        self.entry_reporte.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_browse = ctk.CTkButton(
            file_select_frame,
            text="Examinar",
            width=100,
            fg_color="#3A3D40",
            hover_color="#4A4D50",
            command=self._seleccionar_reporte
        )
        btn_browse.pack(side="left", padx=(0, 10))

        self.btn_procesar = ctk.CTkButton(
            file_select_frame,
            text="⚡ PROCESAR REPORTE",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#00E676",
            hover_color="#00C853",
            text_color="#000000",
            command=self._ejecutar_procesamiento
        )
        self.btn_procesar.pack(side="right")

    def _crear_panel_resumen_y_logs(self):
        """Métricas rápidas y consola de auditoría."""
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)

        # --- PANEL DE MÉTRICAS / TARJETAS ---
        cards_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Tarjeta 1: Total Leídos
        self.card_total = ctk.CTkFrame(cards_frame, fg_color="#1A1C1E", corner_radius=8)
        self.card_total.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkLabel(self.card_total, text="TOTAL LEÍDOS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#A0AAB0").pack(pady=(8, 0))
        self.lbl_num_total = ctk.CTkLabel(self.card_total, text="0", font=ctk.CTkFont(size=20, weight="bold"), text_color="#FFFFFF")
        self.lbl_num_total.pack(pady=(0, 8))

        # Tarjeta 2: Insertados / Actualizados
        self.card_exito = ctk.CTkFrame(cards_frame, fg_color="#1A1C1E", corner_radius=8)
        self.card_exito.grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkLabel(self.card_exito, text="AGREGADOS / ACTUALIZADOS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#00E676").pack(pady=(8, 0))
        self.lbl_num_exito = ctk.CTkLabel(self.card_exito, text="0", font=ctk.CTkFont(size=20, weight="bold"), text_color="#00E676")
        self.lbl_num_exito.pack(pady=(0, 8))

        # Tarjeta 3: Omitidos / Errores
        self.card_omitidos = ctk.CTkFrame(cards_frame, fg_color="#1A1C1E", corner_radius=8)
        self.card_omitidos.grid(row=0, column=2, padx=(5, 0), sticky="ew")
        ctk.CTkLabel(self.card_omitidos, text="NO AGREGADOS / OMITIDOS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#FF5252").pack(pady=(8, 0))
        self.lbl_num_omitidos = ctk.CTkLabel(self.card_omitidos, text="0", font=ctk.CTkFont(size=20, weight="bold"), text_color="#FF5252")
        self.lbl_num_omitidos.pack(pady=(0, 8))

        # --- CONSOLA DE AUDITORÍA / LOGS ---
        log_frame = ctk.CTkFrame(main_container, fg_color="#1A1C1E", corner_radius=10)
        log_frame.grid(row=1, column=0, sticky="nsew")

        lbl_console = ctk.CTkLabel(log_frame, text="💻 CONSOLA DE OPERACIONES EN VIVO", font=ctk.CTkFont(size=11, weight="bold"), text_color="#A0AAB0")
        lbl_console.pack(anchor="w", padx=15, pady=(10, 5))

        self.txt_logs = ctk.CTkTextbox(
            log_frame,
            fg_color="#0D0E0F",
            text_color="#00FF66",
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word"
        )
        self.txt_logs.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.log("SISTEMA LISTO. Selecciona un archivo semanal para iniciar auditoría.")

    def log(self, mensaje: str):
        """Escribe un mensaje en la consola de la interfaz."""
        self.txt_logs.insert("end", f"> {mensaje}\n")
        self.txt_logs.see("end")

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

        # Reiniciar métricas
        self.lbl_num_total.configure(text="0")
        self.lbl_num_exito.configure(text="0")
        self.lbl_num_omitidos.configure(text="0")

        try:
            # Ejecutar el flujo de la aplicación
            resumen = self.core_app.run(self.log, ruta)

            if isinstance(resumen, dict):
                total = resumen.get("total", 0)
                agregados = resumen.get("agregados", 0)
                omitidos = resumen.get("omitidos", 0)
            else:
                total = resumen if isinstance(resumen, int) else 0
                agregados = total
                omitidos = 0

            # Actualizar tarjetas
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