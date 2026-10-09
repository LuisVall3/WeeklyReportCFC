"""Interfaz CCTV NovaSource. Conserva la API WhatsAppTab y send_report."""

from datetime import datetime

from pathlib import Path

from logging.handlers import RotatingFileHandler

from uuid import uuid4

import json

import logging

import re

import threading

import customtkinter as ctk

from tkinter import filedialog, messagebox

from PIL import Image, ImageGrab



ROOT = Path(__file__).resolve().parent.parent

SETTINGS = ROOT / 'whatsapp_settings.json'
DEFAULT_GROUP = 'Emergencias e intrusiones CCTV'

ERROR_LOG_DIR = ROOT / 'data' / 'Logs'

ERROR_LOG_FILE = ERROR_LOG_DIR / 'cctv_errores.log'



CAMARAS_INSTALADAS = {

    'CL204': 32, 'CL210': 9, 'CL213': 26, 'CL121': 30, 'CL122': 27,

    'CL126': 28, 'CL131': 16, 'CL113': 28, 'CL127': 21, 'CL130': 35,

    'CL129': 29, 'CL123': 16, 'CL128': 18, 'CL124': 10, 'CL205': 32,

    'CL209': 14, 'CL114': 28, 'CL132': 10, 'CL120': 26, 'CL125': 30,

    'CL109': 18, 'CL118': 4,

}

PARQUES = [

    'CL204 Batres', 'CL210 BLB', 'CL213 Carena', 'CL121 Chillan I',

    'CL122 Chillan II', 'CL126 El Paso', 'CL131 El Romeral', 'CL113 Lemu',

    'CL127 Linares', 'CL130 Molina', 'CL129 Mutupin', 'CL123 Orion',

    'CL128 Pachira', 'CL124 Pegasus', 'CL205 Pencahue', 'CL209 Pequen',

    'CL114 Rauquen', 'CL132 Santa Carolina', 'CL120 Santa Fe',

    'CL125 Villa Alegre', 'CL109 Villa Cruz', 'CL118 Villa Seca',

]

OPERADORES = ['Bastían Contreras', 'Sebastián Davila', 'Anais Yañez', 'Katherine Garate', 'Matías Guzmán']

BG = '#F2F5FA'

WHITE = '#FFFFFF'

NAVY = '#183B60'

BLUE = '#176CA7'

MUTED = '#64748B'

BORDER = '#E1E8F0'





def total_camaras_parque(nombre):

    match = re.search(r'\bCL\s*[- ]?\s*(\d{3})\b', nombre.upper())

    return CAMARAS_INSTALADAS.get(f'CL{match.group(1)}') if match else None





def _codigo_error(exc):

    name, detail = type(exc).__name__.lower(), str(exc).lower()

    if 'invalid session id' in detail or 'disconnected' in detail or 'invalidsessionid' in name:

        return 'CCTV-WA-003'

    if 'timeout' in name or 'timeout' in detail:

        return 'CCTV-WA-004'

    if any(x in detail for x in ('no such file', 'no existe', 'file not found')):

        return 'CCTV-IMG-002'

    if 'seguridad' in detail or 'chat incorrecto' in detail:

        return 'CCTV-WA-002'

    return 'CCTV-WA-001'





def _registrar_error_cctv(exc, parque, grupo, image_path):

    incidente = f'{_codigo_error(exc)}-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:6].upper()}'

    try:

        ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger('weeklyreportcfc.cctv.errors')

        logger.setLevel(logging.ERROR)

        logger.propagate = False

        if not logger.handlers:

            handler = RotatingFileHandler(ERROR_LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding='utf-8')

            handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))

            logger.addHandler(handler)

        logger.error('Incidente=%s | Parque=%r | Grupo=%r | Imagen=%r | Tipo=%s | Detalle=%s',

                     incidente, parque, grupo, str(image_path) if image_path else None,

                     type(exc).__name__, str(exc), exc_info=(type(exc), exc, exc.__traceback__))

    except Exception as log_exc:

        print(f'[CCTV] Error escribiendo log: {log_exc}')

    return incidente







class SelectorCorporativo(ctk.CTkFrame):

    """Selector moderno con lista desplazable y filtro opcional."""

    def __init__(self, master, values, command=None, searchable=False, **kwargs):

        super().__init__(master, fg_color='#F7F9FC', border_color=BORDER,

                         border_width=1, corner_radius=9, height=40, **kwargs)

        self.values = list(values)

        self.command = command

        self.searchable = searchable

        self._value = self.values[0] if self.values else ''

        self._popup = None

        self.grid_columnconfigure(0, weight=1)

        self.grid_propagate(False)

        self.display = ctk.CTkButton(

            self, text=self._value, anchor='w', height=38,

            fg_color='transparent', hover_color='#EDF4FB',

            text_color=NAVY, corner_radius=8,

            font=ctk.CTkFont(size=12), command=self._toggle

        )

        self.display.grid(row=0, column=0, sticky='nsew', padx=(3, 0))

        self.arrow = ctk.CTkButton(

            self, text='⌄', width=35, height=36,

            fg_color='transparent', hover_color='#EDF4FB',

            text_color=BLUE, corner_radius=8,

            font=ctk.CTkFont(size=20), command=self._toggle

        )

        self.arrow.grid(row=0, column=1, padx=(0, 3), pady=1)



    def get(self):

        return self._value



    def set(self, value):

        self._value = str(value)

        self.display.configure(text=self._value)



    def configure(self, **kwargs):

        if 'values' in kwargs:

            self.values = list(kwargs.pop('values'))

            if self._popup is not None:

                self._close()

        super().configure(**kwargs)



    def _toggle(self):

        if self._popup is not None:

            self._close()

        else:

            self._open()



    def _close(self):

        popup = self._popup

        self._popup = None

        if popup is not None:

            try:

                popup.destroy()

            except Exception:

                pass



    def _select(self, value):

        self.set(value)

        self._close()

        if self.command:

            self.command(value)



    def _open(self):

        if not self.winfo_exists():

            return

        top = self.winfo_toplevel()

        self.update_idletasks()

        x = self.winfo_rootx()

        y = self.winfo_rooty() + self.winfo_height() + 3

        width = max(self.winfo_width(), 180)

        screen_h = self.winfo_screenheight()

        desired = min(360, 54 + 39 * min(len(self.values), 7))

        if y + desired > screen_h - 55:

            y = max(10, self.winfo_rooty() - desired - 3)



        popup = ctk.CTkToplevel(top)

        self._popup = popup

        popup.withdraw()

        popup.overrideredirect(True)

        popup.geometry(f'{width}x{desired}+{x}+{y}')

        popup.configure(fg_color=WHITE)

        popup.attributes('-topmost', True)



        frame = ctk.CTkFrame(popup, fg_color=WHITE, corner_radius=10,

                             border_width=1, border_color=BORDER)

        frame.pack(fill='both', expand=True)

        if self.searchable:

            search = ctk.CTkEntry(frame, placeholder_text='Buscar parque...',

                                  height=34, border_color=BORDER)

            search.pack(fill='x', padx=9, pady=(9, 5))

        else:

            search = None



        list_frame = ctk.CTkScrollableFrame(frame, fg_color='transparent',

                                            corner_radius=0)

        list_frame.pack(fill='both', expand=True, padx=5, pady=(4, 7))



        def render(filter_text=''):

            for child in list_frame.winfo_children():

                child.destroy()

            matches = [v for v in self.values if filter_text.casefold() in v.casefold()]

            for value in matches:

                selected = value == self._value

                ctk.CTkButton(

                    list_frame, text=('✓  ' if selected else '    ') + value,

                    anchor='w', height=35, corner_radius=6,

                    fg_color='#EAF2FA' if selected else 'transparent',

                    hover_color='#E8F1FB',

                    text_color=BLUE if selected else NAVY,

                    font=ctk.CTkFont(size=12),

                    command=lambda v=value: self._select(v)

                ).pack(fill='x', pady=1)

            if not matches:

                ctk.CTkLabel(list_frame, text='Sin coincidencias',

                             text_color=MUTED).pack(pady=12)



        if search is not None:

            search.bind('<KeyRelease>', lambda _event: render(search.get()))

        render()

        popup.deiconify()

        popup.lift()

        # Cerrar al cambiar a otra ventana, sin bloquear la GUI.

        popup.bind('<Escape>', lambda _event: self._close())

        popup.bind('<FocusOut>', lambda _event: self.after(130, self._close_if_unfocused))

        if search is not None:

            search.focus_set()

        else:

            popup.focus_set()



    def _close_if_unfocused(self):

        if self._popup is None:

            return

        try:

            focus = self._popup.focus_get()

            if focus is None or not str(focus).startswith(str(self._popup)):

                self._close()

        except Exception:

            self._close()





class WhatsAppTab(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(master, fg_color=BG)

        self.image = None

        self.image_path = None

        self.preview_image = None

        self._sending = False

        self._build()

        self.winfo_toplevel().bind('<Control-v>', self._paste_shortcut, add='+')



    def _label(self, parent, text):

        return ctk.CTkLabel(parent, text=text, text_color=NAVY,

                            font=ctk.CTkFont(size=12, weight='bold'), anchor='w')



    def _card(self, parent, title, subtitle=None):

        card = ctk.CTkFrame(parent, fg_color=WHITE, corner_radius=14,

                            border_width=1, border_color=BORDER)

        header = ctk.CTkFrame(card, fg_color='transparent')

        header.pack(fill='x', padx=22, pady=(17, 9))

        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=16, weight='bold'),

                     text_color=NAVY, anchor='w').pack(fill='x')

        if subtitle:

            ctk.CTkLabel(header, text=subtitle, text_color=MUTED, font=ctk.CTkFont(size=12),

                         anchor='w').pack(fill='x', pady=(2, 0))

        body = ctk.CTkFrame(card, fg_color='transparent')

        body.pack(fill='x', padx=22, pady=(0, 19))

        return card, body



    def _field(self, parent, label, widget, row, column=0, span=1):

        self._label(parent, label).grid(row=row*2, column=column, columnspan=span,

                                        sticky='w', padx=(0, 12), pady=(9, 4))

        widget.grid(row=row*2+1, column=column, columnspan=span, sticky='ew',

                    padx=(0, 12), pady=(0, 5))



    def _build(self):

        self.grid_columnconfigure(0, weight=1)

        self.grid_rowconfigure(0, weight=1)

        self.form = ctk.CTkScrollableFrame(self, fg_color='transparent', corner_radius=0)

        self.form.grid(row=0, column=0, sticky='nsew', padx=(18, 8), pady=(12, 0))

        self.form.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(self.form, fg_color='transparent')

        content.grid(row=0, column=0, sticky='n', pady=(0, 12))

        content.configure(width=880)

        content.grid_propagate(True)

        content.grid_columnconfigure(0, weight=1)



        title = ctk.CTkFrame(content, fg_color='transparent')

        title.grid(row=0, column=0, sticky='ew', pady=(0, 12))

        ctk.CTkLabel(title, text='Reporte de cámaras CCTV', text_color=NAVY,

                     font=ctk.CTkFont(size=24, weight='bold')).pack(anchor='w')

        ctk.CTkLabel(title, text='Disponibilidad de cámaras y envío de evidencia a WhatsApp',

                     text_color=MUTED, font=ctk.CTkFont(size=12)).pack(anchor='w', pady=(3, 0))



        card, b = self._card(content, '01  Información del parque', 'Selecciona el parque y verifica la fecha del reporte.')

        card.grid(row=1, column=0, sticky='ew', pady=(0, 12))

        b.grid_columnconfigure((0, 1), weight=1, uniform='info')

        self.park = SelectorCorporativo(

            b, PARQUES, searchable=True,

            command=lambda value: self._actualizar_total_camaras(value)

        )

        self._field(b, 'Parque fotovoltaico', self.park, 0, 0, 2)

        now = datetime.now()

        self.date = ctk.CTkEntry(b, height=38, border_color=BORDER)

        self.date.insert(0, now.strftime('%d-%m-%Y'))

        self.time = ctk.CTkEntry(b, height=38, border_color=BORDER)

        self.time.insert(0, now.strftime('%H:%M'))

        self._field(b, 'Fecha (DD-MM-AAAA)', self.date, 1, 0)

        self._field(b, 'Hora (HH:MM)', self.time, 1, 1)

        ctk.CTkButton(b, text='Actualizar fecha y hora', command=self.refresh_clock,

                      fg_color='#EAF2FA', hover_color='#DDEAF8', text_color=BLUE,

                      height=34).grid(row=4, column=0, columnspan=2, sticky='w', pady=(8, 0))



        card, b = self._card(content, '02  Estado de cámaras', 'El total instalado se obtiene automáticamente del parque.')

        card.grid(row=2, column=0, sticky='ew', pady=(0, 12))

        b.grid_columnconfigure((0, 1), weight=1, uniform='cams')

        self.cameras = SelectorCorporativo(

            b, [str(i) for i in range(33)],

            command=lambda _value: self._update_availability()

        )

        self.cameras.set('0')

        self.total_cameras = ctk.CTkEntry(b, height=40, state='normal', border_color=BORDER)

        self._field(b, 'Cámaras disponibles', self.cameras, 0, 0)

        self._field(b, 'Total instaladas (automático)', self.total_cameras, 0, 1)

        self.availability = ctk.CTkLabel(b, text='', text_color=MUTED, anchor='w')

        self.availability.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(8, 2))

        self.progress = ctk.CTkProgressBar(b, height=9, progress_color=BLUE, fg_color='#E8EFF7')

        self.progress.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(0, 5))

        self._actualizar_total_camaras(self.park.get())



        card, b = self._card(content, '03  Datos del reporte', 'Identifica al operador y registra las novedades del turno.')

        card.grid(row=3, column=0, sticky='ew', pady=(0, 12))

        b.grid_columnconfigure((0, 1), weight=1, uniform='report')

        self.operador_cctv = SelectorCorporativo(b, OPERADORES)

        self.operador_cctv.set(OPERADORES[0])

        self.group = ctk.CTkEntry(b, height=40, placeholder_text='Nombre exacto del grupo', border_color=BORDER)

        self._field(b, 'Operador CCTV', self.operador_cctv, 0, 0)

        self._field(b, 'Grupo de WhatsApp', self.group, 0, 1)

        # Grupo operacional predeterminado; editable para pruebas.
        self.group.insert(0, DEFAULT_GROUP)

        self._label(b, 'Novedades del parque').grid(row=2, column=0, columnspan=2, sticky='w', pady=(13, 5))

        self.novedades = ctk.CTkTextbox(b, height=90, wrap='word', fg_color='#F7F9FC',

                                         border_width=1, border_color=BORDER)

        self.novedades.grid(row=3, column=0, columnspan=2, sticky='ew')

        ctk.CTkLabel(b, text='Obligatorias cuando existan cámaras fuera de servicio.',

                     text_color=MUTED, font=ctk.CTkFont(size=11)).grid(

                         row=4, column=0, columnspan=2, sticky='w', pady=(5, 0))



        card, b = self._card(content, '04  Evidencia fotográfica', 'Adjunta una fotografía o pega una captura de pantalla.')

        card.grid(row=4, column=0, sticky='ew', pady=(0, 12))

        self.preview_area = ctk.CTkFrame(b, fg_color='#F7F9FC', corner_radius=10,

                                          border_width=1, border_color=BORDER, height=165)

        self.preview_area.pack(fill='x')

        self.preview_area.pack_propagate(False)

        self.preview = ctk.CTkLabel(self.preview_area, text='Sin captura adjunta', text_color=MUTED)

        self.preview.pack(expand=True)

        actions = ctk.CTkFrame(b, fg_color='transparent')

        actions.pack(pady=(12, 0))

        ctk.CTkButton(actions, text='Adjuntar imagen', command=self.attach,

                      fg_color=BLUE, hover_color=NAVY, height=36).pack(side='left', padx=5)

        ctk.CTkButton(actions, text='Pegar captura', command=self.paste,

                      fg_color='#EAF2FA', hover_color='#DDEAF8', text_color=BLUE,

                      height=36).pack(side='left', padx=5)



        card, b = self._card(content, '05  Vista previa del mensaje', 'El texto se genera al confirmar el reporte.')

        card.grid(row=5, column=0, sticky='ew', pady=(0, 12))

        self.message = ctk.CTkTextbox(b, height=140, fg_color='#F7F9FC',

                                       border_width=1, border_color=BORDER, wrap='word')

        self.message.pack(fill='x')



        footer = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=0,

                              border_width=1, border_color=BORDER)

        footer.grid(row=1, column=0, sticky='ew')

        footer.grid_columnconfigure(0, weight=1)

        self.send_button = ctk.CTkButton(footer, text='Enviar reporte a WhatsApp',

                                          command=self.send_automated, height=43,

                                          fg_color=BLUE, hover_color=NAVY,

                                          font=ctk.CTkFont(size=14, weight='bold'))

        self.send_button.grid(row=0, column=0, sticky='ew', padx=24, pady=(12, 4))

        self.status = ctk.CTkLabel(footer, text='Listo para preparar reporte',

                                   text_color=MUTED, height=22)

        self.status.grid(row=1, column=0, pady=(0, 9))



    def _actualizar_total_camaras(self, parque):

        total = total_camaras_parque(parque)

        self.total_cameras.configure(state='normal')

        self.total_cameras.delete(0, 'end')

        self.total_cameras.insert(0, str(total) if total is not None else '')

        self.total_cameras.configure(state='disabled')

        if total is not None:

            self.cameras.configure(values=[str(i) for i in range(total + 1)])

            try:

                if int(self.cameras.get()) > total:

                    self.cameras.set(str(total))

            except ValueError:

                self.cameras.set('0')

        self._update_availability()



    def _update_availability(self):

        total = total_camaras_parque(self.park.get())

        try:

            count = int(self.cameras.get())

        except ValueError:

            count = -1

        if not total or count < 0 or count > total:

            self.availability.configure(text='Ingresa una cantidad válida de cámaras disponibles.', text_color='#B45309')

            self.progress.set(0)

            return

        missing = total - count

        self.availability.configure(

            text=f'Disponibilidad: {count / total:.1%}  ·  {missing} cámara(s) fuera de servicio',

            text_color='#B45309' if missing else '#16805D')

        self.progress.configure(progress_color='#E2A33B' if missing else '#169B77')

        self.progress.set(count / total)



    def refresh_clock(self):

        now = datetime.now()

        for entry, value in ((self.date, now.strftime('%d-%m-%Y')), (self.time, now.strftime('%H:%M'))):

            entry.delete(0, 'end')

            entry.insert(0, value)



    def _set_image(self, img):

        self.image = img.convert('RGB').copy()

        w, h = self.image.size

        factor = min(490 / w, 140 / h, 1)

        size = (max(1, int(w * factor)), max(1, int(h * factor)))

        self.preview_image = ctk.CTkImage(light_image=self.image, dark_image=self.image, size=size)

        self.preview.configure(image=self.preview_image, text='')



    def attach(self):

        path = filedialog.askopenfilename(filetypes=[('Imágenes', '*.png *.jpg *.jpeg *.webp *.bmp')])

        if path:

            try:

                with Image.open(path) as img:

                    self._set_image(img)

                self.image_path = path

            except Exception as exc:

                messagebox.showerror('Imagen inválida', str(exc))



    def _paste_shortcut(self, event):

        if isinstance(event.widget, (ctk.CTkEntry, ctk.CTkTextbox)) or event.widget.winfo_class() in ('Entry', 'Text'):

            return

        self.paste()



    def paste(self):

        try:

            item = ImageGrab.grabclipboard()

            if isinstance(item, Image.Image):

                self._set_image(item)

                self.image_path = None

            elif isinstance(item, list) and item and Path(item[0]).is_file():

                with Image.open(item[0]) as img:

                    self._set_image(img)

                self.image_path = item[0]

            else:

                messagebox.showinfo('Portapapeles', 'No se encontró una imagen. Copia una captura e inténtalo nuevamente.')

        except Exception as exc:

            messagebox.showerror('Portapapeles', f'No se pudo leer la captura: {exc}')



    def send_automated(self):

        if self._sending:

            return

        try:

            datetime.strptime(self.date.get().strip() + ' ' + self.time.get().strip(), '%d-%m-%Y %H:%M')

            count = int(self.cameras.get())

            total = total_camaras_parque(self.park.get())

            if total is None or count < 0 or count > total:

                raise ValueError('Cámaras inválidas')

        except ValueError:

            messagebox.showerror('Datos inválidos', 'Revisa fecha, hora y cámaras disponibles.')

            return

        group_name = self.group.get().strip()

        if not group_name:

            messagebox.showerror('Grupo requerido', 'Escribe el nombre exacto del grupo de WhatsApp.')

            return

        novedades = self.novedades.get('1.0', 'end-1c').strip()

        if count < total and not novedades:

            messagebox.showwarning('Novedad obligatoria',

                                   f'El parque tiene {total} cámaras instaladas y solo {count} disponibles '

                                   f'({total-count} no disponibles).\n\nDebes indicar la novedad antes de enviar.')

            self.novedades.focus_set()

            return

        message = (

            f'⚡ *Parque:* {self.park.get()}\n'

            f'📅 *Fecha:* {self.date.get().strip()}\n'

            f'🕒 *Hora:* {self.time.get().strip()}\n'

            f'📸 *Cámaras disponibles:* {count}/{total}\n'

            f'📌 *Novedades:* {novedades if novedades else "Sin novedades"}\n'

            f'👤 *Operador CCTV:* {self.operador_cctv.get()}'

        )

        self.message.delete('1.0', 'end')

        self.message.insert('1.0', message)

        try:

            SETTINGS.write_text(json.dumps({'group_name': group_name}, ensure_ascii=False, indent=2), encoding='utf-8')

        except OSError:

            pass

        image_path = None

        if self.image is not None:

            try:

                folder = ROOT / 'data' / 'CapturasCCTV'

                folder.mkdir(parents=True, exist_ok=True)

                image_path = (folder / f'CCTV_{datetime.now():%Y%m%d_%H%M%S_%f}.png').resolve()

                self.image.save(image_path, format='PNG')

                if not image_path.is_file() or image_path.stat().st_size == 0:

                    raise OSError('La fotografía no se guardó correctamente.')

                with Image.open(image_path) as img:

                    img.verify()

            except Exception as exc:

                incidente = _registrar_error_cctv(exc, self.park.get(), group_name, image_path)

                messagebox.showerror('No se pudo preparar el reporte',

                                     f'Contáctese con soporte técnico.\nCódigo de error: {incidente}')

                return

        if not messagebox.askyesno('Confirmar envío',

                                   f'¿Enviar reporte de {self.park.get()} al grupo «{group_name}»?'):

            return

        self._sending = True

        self.send_button.configure(state='disabled', text='Enviando reporte...')

        self.status.configure(text='Abriendo WhatsApp Web...')

        parque = self.park.get()



        def worker():

            try:

                from .whatsapp_sender import send_report

                result = send_report(group_name, message, str(image_path) if image_path else None)

                self.after(0, lambda r=result: self._finish_send(r, False))

            except Exception as exc:

                incidente = _registrar_error_cctv(exc, parque, group_name, image_path)

                self.after(0, lambda code=incidente: self._finish_send(code, True))



        threading.Thread(target=worker, daemon=True).start()



    def _finish_send(self, detail, error):

        self._sending = False

        self.send_button.configure(state='normal', text='Enviar reporte a WhatsApp')

        self.status.configure(text='No se pudo confirmar el envío' if error else 'Envío ejecutado; revisa WhatsApp Web')

        if error:

            messagebox.showerror('No se pudo completar la operación',

                                 'No se pudo confirmar la operación.\n\n'

                                 'Contáctese con soporte técnico.\n'

                                 f'Código de error: {detail}\n\n'

                                 'Revisa el grupo antes de volver a enviar el reporte.')

        else:

            messagebox.showinfo('WhatsApp Web', str(detail))
