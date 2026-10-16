
"""
WeeklyReportCFC - WhatsApp Sender
Automatización de reportes CCTV mediante WhatsApp Web.
Flujo:
1. Abrir WhatsApp Web.
2. Buscar el grupo por nombre exacto.
3. Verificar el título real del chat.
4. Adjuntar fotografía.
5. Escribir el reporte como descripción.
6. Confirmar destinatario.
7. Enviar una sola vez.
8. En envíos individuales, verificar el historial. En cola, continuar
   tras cerrarse el editor de la foto sin inspeccionar el historial.
Dependencias:
    py -m pip install selenium pillow
"""
from pathlib import Path
from datetime import datetime
import logging
import time
import threading
import unicodedata
from PIL import Image, ImageOps
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
)
# ============================================================# CONFIGURACIÓN# ============================================================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "[WhatsApp] %(asctime)s - %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(handler)
SEND_LOCK = threading.Lock()
from src.paths import APP_DIR as ROOT
DEBUG_DIR = ROOT / "data" / "WhatsAppDebug"
TEMP_DIR = ROOT / "data" / "WhatsAppTemp"
PROFILE = (
    Path.home()
    / "AppData"
    / "Local"
    / "WeeklyReportCFC"
    / "ChromeWhatsApp"
)
class WhatsAppSendError(RuntimeError):
    """Error controlado del módulo WhatsApp."""
    pass
# ============================================================# UTILIDADES# ============================================================
def esperar(driver, seconds=30):
    return WebDriverWait(
        driver,
        seconds,
        poll_frequency=0.4,
        ignored_exceptions=(
            StaleElementReferenceException,
        ),
    )
def visible(context, by, selector):
    for element in context.find_elements(by, selector):
        try:
            if element.is_displayed() and element.is_enabled():
                return element
        except StaleElementReferenceException:
            continue
    return False
def normalizar(text):
    text = unicodedata.normalize(
        "NFC",
        str(text or ""),
    )
    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")
    text = text.replace("\ufe0f", "")
    text = text.replace("\ufe0e", "")
    return " ".join(text.split())
def click_seguro(driver, element):
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});",
        element,
    )
    try:
        element.click()
    except (
        ElementClickInterceptedException,
        ElementNotInteractableException,
    ):
        ActionChains(driver).move_to_element(
            element
        ).pause(0.2).click().perform()
def guardar_diagnostico(driver, stage):
    DEBUG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    screenshot = DEBUG_DIR / f"{stage}_{stamp}.png"
    html_file = DEBUG_DIR / f"{stage}_{stamp}.html"
    try:
        driver.save_screenshot(str(screenshot))
        logger.error(
            "Captura de diagnóstico: %s",
            screenshot,
        )
    except Exception:
        pass
    try:
        html_file.write_text(
            driver.page_source,
            encoding="utf-8",
        )
        logger.error(
            "HTML de diagnóstico: %s",
            html_file,
        )
    except Exception:
        pass
# ============================================================# BÚSQUEDA DEL GRUPO# ============================================================
def barra_busqueda(driver):
    selectors = [
        '#side [contenteditable="true"][role="textbox"]',
        '#side [contenteditable="true"]',
        '[contenteditable="true"][aria-label="Search input textbox"]',
        'input[placeholder="Search or start a new chat"]',
        'input[placeholder="Buscar un chat o iniciar uno nuevo"]',
    ]
    for selector in selectors:
        element = visible(
            driver,
            By.CSS_SELECTOR,
            selector,
        )
        if element:
            return element
    return False
# ============================================================# IDENTIFICAR NOMBRE REAL DEL CHAT# ============================================================
def nombre_chat_abierto(driver):
    """
    Obtiene el nombre del chat desde el encabezado.
    No debe utilizar la lista de participantes.
    """
    selectors = [
        '#main header [data-testid="conversation-info-header-chat-title"]',
        '#main header [data-testid="conversation-info-header-chat-title"] span',
        '#main header span[dir="auto"][title]',
        '#main header [role="button"] span[title]',
    ]
    for selector in selectors:
        elements = driver.find_elements(
            By.CSS_SELECTOR,
            selector,
        )
        for element in elements:
            try:
                if not element.is_displayed():
                    continue
                title = (
                    element.get_attribute("title")
                    or element.text
                    or ""
                ).strip()
                if title:
                    logger.info(
                        "Nombre detectado en encabezado: %s",
                        title,
                    )
                    return title
            except StaleElementReferenceException:
                continue
    return ""
def grupo_abierto(driver, group_name):
    """
    Comprueba el nombre exacto del grupo en el encabezado.
    Evita confundir el nombre del grupo con
    los nombres de sus participantes.
    """
    headers = driver.find_elements(
        By.CSS_SELECTOR,
        "#main header",
    )
    if not headers:
        return False
    expected = normalizar(group_name)
    selectors = [
        '[data-testid="conversation-info-header-chat-title"]',
        'span[title]',
    ]
    for selector in selectors:
        elements = headers[0].find_elements(
            By.CSS_SELECTOR,
            selector,
        )
        for element in elements:
            try:
                if not element.is_displayed():
                    continue
                actual = (
                    element.get_attribute("title")
                    or element.text
                    or ""
                ).strip()
                if normalizar(actual) == expected:
                    logger.info(
                        "Grupo verificado correctamente: %s",
                        actual,
                    )
                    return True
            except StaleElementReferenceException:
                continue
    return False
def verificar_destinatario(driver, group_name):
    """
    Validación obligatoria antes del envío.
    """
    if not grupo_abierto(driver, group_name):
        actual = nombre_chat_abierto(driver)
        raise WhatsAppSendError(
            "SEGURIDAD: no se pudo confirmar "
            f"el grupo «{group_name}». "
            f"Texto detectado: «{actual}». "
            "Envío cancelado."
        )
    logger.info(
        "SEGURIDAD: destinatario confirmado: %s",
        group_name,
    )
# ============================================================# RESULTADO EXACTO DEL GRUPO# ============================================================
def buscar_titulo_exacto(driver, group_name):
    """
    Busca un chat cuyo título coincida exactamente
    con el nombre solicitado.
    No utiliza el contenido de los mensajes.
    """
    elements = driver.find_elements(
        By.CSS_SELECTOR,
        '#pane-side span[title]',
    )
    matches = []
    seen = set()
    for element in elements:
        try:
            if not element.is_displayed():
                continue
            title = (
                element.get_attribute("title") or ""
            ).strip()
            if normalizar(title) != normalizar(group_name):
                continue
            if element.id in seen:
                continue
            seen.add(element.id)
            matches.append(element)
        except StaleElementReferenceException:
            continue
    return matches
def abrir_grupo(driver, group_name):
    logger.info(
        "Buscando grupo exacto: %s",
        group_name,
    )
    if grupo_abierto(driver, group_name):
        logger.info(
            "Grupo correcto ya abierto."
        )
        return
    search = esperar(driver, 60).until(
        barra_busqueda
    )
    click_seguro(driver, search)
    search.send_keys(
        Keys.CONTROL,
        "a",
    )
    search.send_keys(group_name)
    logger.info(
        "Esperando resultados..."
    )
    try:
        matches = esperar(driver, 30).until(
            lambda d: (
                buscar_titulo_exacto(d, group_name)
                or False
            )
        )
    except TimeoutException as exc:
        raise WhatsAppSendError(
            f"No se encontró el chat exacto "
            f"«{group_name}»."
        ) from exc
    matches = buscar_titulo_exacto(
        driver,
        group_name,
    )
    if len(matches) != 1:
        raise WhatsAppSendError(
            f"Se encontraron {len(matches)} coincidencias "
            f"exactas para «{group_name}». "
            "No se abrirá ningún chat."
        )
    logger.info(
        "Título exacto encontrado."
    )
    click_seguro(
        driver,
        matches[0],
    )
    try:
        esperar(driver, 20).until(
            lambda d: grupo_abierto(
                d,
                group_name,
            )
        )
    except TimeoutException as exc:
        actual = nombre_chat_abierto(driver)
        raise WhatsAppSendError(
            "SEGURIDAD: chat incorrecto. "
            f"Esperado: «{group_name}». "
            f"Detectado: «{actual}». "
            "No se enviará el reporte."
        ) from exc
    logger.info(
        "Grupo abierto y verificado: %s",
        group_name,
    )
# ============================================================# EDITOR PRINCIPAL# ============================================================
def editor_principal(driver):
    selectors = [
        '#main footer [contenteditable="true"][role="textbox"]',
        '#main footer [contenteditable="true"]',
        '#main [data-testid="conversation-compose-box-input"]',
    ]
    for selector in selectors:
        element = visible(
            driver,
            By.CSS_SELECTOR,
            selector,
        )
        if element:
            return element
    return False
def escribir_multilinea(driver, editor, message):
    click_seguro(driver, editor)
    for index, line in enumerate(
        message.split("\n")
    ):
        if index:
            ActionChains(driver).key_down(
                Keys.SHIFT
            ).send_keys(
                Keys.ENTER
            ).key_up(
                Keys.SHIFT
            ).perform()
        if line:
            editor.send_keys(line)
# ============================================================# PREPARACIÓN DE IMAGEN# ============================================================
def preparar_imagen(image_path):
    original = Path(image_path).resolve()
    if not original.is_file():
        raise WhatsAppSendError(
            f"No existe la fotografía: {original}"
        )
    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    output = TEMP_DIR / f"CCTV_{stamp}.jpg"
    try:
        with Image.open(original) as image:
            image = ImageOps.exif_transpose(image)
            if (
                image.mode in ("RGBA", "LA")
                or "transparency" in image.info
            ):
                rgba = image.convert("RGBA")
                background = Image.new(
                    "RGB",
                    rgba.size,
                    (255, 255, 255),
                )
                background.paste(
                    rgba,
                    mask=rgba.getchannel("A"),
                )
                image = background
            else:
                image = image.convert("RGB")
            image.save(
                output,
                "JPEG",
                quality=92,
            )
    except Exception as exc:
        raise WhatsAppSendError(
            f"No se pudo preparar la imagen: {exc}"
        ) from exc
    logger.info(
        "Fotografía preparada: %s",
        output.name,
    )
    return output
# ============================================================# ADJUNTAR FOTOGRAFÍA# ============================================================
def boton_adjuntar(driver):
    editor = editor_principal(driver)
    if not editor:
        return False
    footer = editor.find_element(
        By.XPATH,
        "./ancestor::footer[1]",
    )
    selectors = [
        '[data-testid="attach-menu-plus"]',
        'button[title="Attach"]',
        'button[title="Adjuntar"]',
        '[aria-label="Attach"]',
        '[aria-label="Adjuntar"]',
        'button[aria-label*="Attach" i]',
        'button[aria-label*="Adjuntar" i]',
    ]
    for selector in selectors:
        element = visible(
            footer,
            By.CSS_SELECTOR,
            selector,
        )
        if element:
            return element
    return False
def input_fotografias(driver):
    """
    Input de Photos & videos.
    Según las pruebas anteriores:
        accept="*"
        multiple=true
    No selecciona el input de stickers.
    """
    inputs = driver.find_elements(
        By.CSS_SELECTOR,
        'input[type="file"]',
    )
    for element in inputs:
        try:
            accept = (
                element.get_attribute("accept") or ""
            ).strip().lower()
            multiple = (
                element.get_dom_attribute("multiple")
                is not None
            )
            if (
                multiple
                and accept in (
                    "*",
                    "*/*",
                    "image/*,video/*",
                    "image/*, video/*",
                )
            ):
                return element
        except (
            StaleElementReferenceException,
            WebDriverException,
        ):
            continue
    return False
def campo_descripcion(driver):
    """Encuentra solamente el campo editable de descripción de la imagen."""
    containers = driver.find_elements(
        By.CSS_SELECTOR,
        '[data-testid="media-caption-input-container"]'
    )
    if len([c for c in containers if c.is_displayed()]) != 1:
        return False
    container = next(c for c in containers if c.is_displayed())
    if container.get_attribute('contenteditable') == 'true':
        return container
    editors = container.find_elements(
        By.CSS_SELECTOR,
        '[contenteditable="true"]'
    )
    editors = [e for e in editors if e.is_displayed()]
    return editors[0] if len(editors) == 1 else False
def cargar_fotografia(driver, photo):
    """Abre Photos & videos y pega la ruta exacta en el diálogo de Windows.

    Evita el input image/*, que en esta versión corresponde al editor de stickers.
    """
    import time
    import pyautogui
    import pyperclip

    photo = Path(photo).resolve(strict=True)
    if not photo.is_file() or photo.stat().st_size == 0:
        raise WhatsAppSendError(f"Fotografía inválida: {photo}")

    logger.info("Fotografía validada: %s", photo)
    attach = esperar(driver, 20).until(boton_adjuntar)
    click_seguro(driver, attach)
    logger.info("Menú de adjuntos abierto.")

    # Compatible con WhatsApp Web en español e inglés.
    # Se selecciona la opción del menú, nunca el input de stickers.
    def opcion_fotos(d):
        for item in d.find_elements(By.CSS_SELECTOR, '[role="menuitem"]'):
            try:
                if not item.is_displayed() or not item.is_enabled():
                    continue
                etiqueta = normalizar(
                    (item.get_attribute("aria-label") or "") + " " + (item.text or "")
                ).casefold()
                if any(nombre in etiqueta for nombre in (
                    "photos & videos", "fotos y videos", "fotos e vídeos"
                )):
                    return item
            except StaleElementReferenceException:
                continue
        return False

    try:
        opcion = esperar(driver, 15).until(opcion_fotos)
    except TimeoutException as exc:
        raise WhatsAppSendError(
            "No se encontró Fotos y videos / Photos & videos en el menú. "
            "No se envió ningún mensaje."
        ) from exc

    # Copiar antes de abrir el diálogo: evita que escribir la ruta pierda letras.
    pyperclip.copy(str(photo))
    if pyperclip.paste() != str(photo):
        raise WhatsAppSendError("No se pudo copiar la ruta de la fotografía.")

    logger.info("Abriendo Photos & videos (diálogo de Windows)...")
    click_seguro(driver, opcion)
    time.sleep(2)

    # Alt+N enfoca el campo Nombre de archivo en el diálogo Abrir de Windows.
    # Ctrl+V pega la ruta completa, sin depender de la distribución del teclado.
    pyautogui.hotkey("alt", "n")
    time.sleep(0.35)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.6)
    pyautogui.press("enter")

    logger.info("Ruta pegada; esperando vista previa de fotografía...")
    try:
        esperar(driver, 35).until(campo_descripcion)
    except TimeoutException as exc:
        raise WhatsAppSendError(
            "No apareció la vista previa con descripción. Comprueba si "
            "el diálogo Abrir quedó abierto o si otra ventana tomó el foco. "
            "No se envió ningún mensaje."
        ) from exc

    logger.info("Vista previa de fotografía detectada correctamente.")

def obtener_descripcion(driver, element):
    return driver.execute_script(
        """
        const el = arguments[0];
        return el.innerText || el.textContent || "";
        """,
        element,
    )
def escribir_descripcion(driver, message):
    logger.info(
        "Escribiendo reporte CCTV en descripción..."
    )
    caption = esperar(driver, 25).until(
        campo_descripcion
    )
    escribir_multilinea(
        driver,
        caption,
        message,
    )
    def verificar(d):
        current = campo_descripcion(d)
        if not current:
            return False
        actual = obtener_descripcion(
            d,
            current,
        )
        return (
            bool(normalizar(message))
            and normalizar(message) in normalizar(actual)
        )
    try:
        esperar(driver, 15).until(
            verificar
        )
    except TimeoutException as exc:
        raise WhatsAppSendError(
            "No se pudo verificar la descripción. "
            "No se enviará la fotografía."
        ) from exc
    logger.info(
        "Descripción verificada correctamente."
    )
# ============================================================# BOTÓN DE ENVÍO# ============================================================
def boton_enviar_imagen(driver):
    """Detecta Enviar / Send solo en la vista previa de la fotografía."""
    caption = campo_descripcion(driver)
    if not caption:
        return False
    selectors = (
        '[role="button"][aria-label^="Send" i]',
        '[role="button"][aria-label^="Enviar" i]',
        'button[aria-label^="Send" i]',
        'button[aria-label^="Enviar" i]',
        '[data-icon="wds-ic-send-filled"]',
        '[data-icon="send"]',
    )
    candidatos = []
    identificados = set()
    for selector in selectors:
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            try:
                boton = driver.execute_script(
                    "return arguments[0].closest('button, [role=button]') || arguments[0];",
                    element,
                )
                if not boton.is_displayed() or not boton.is_enabled():
                    continue
                # Excluye el botón de enviar texto del chat principal.
                if driver.execute_script(
                    "return !!arguments[0].closest('#main footer');", boton
                ):
                    continue
                # Exige un contenedor compartido con la descripción de la foto.
                if not driver.execute_script("""
                    const boton = arguments[0], descripcion = arguments[1];
                    let padre = descripcion;
                    for (let i = 0; padre && i < 10; i++, padre = padre.parentElement) {
                        if (padre.contains(boton) && !padre.matches('body, html, #main'))
                            return true;
                    }
                    return false;
                """, boton, caption):
                    continue
                identificador = boton.id
                if identificador not in identificados:
                    identificados.add(identificador)
                    candidatos.append(boton)
            except (StaleElementReferenceException, WebDriverException):
                continue
    if len(candidatos) != 1:
        logger.info('Botones de envío de fotografía encontrados: %s', len(candidatos))
        return False
    return candidatos[0]

def mensajes_salientes(driver):
    return driver.find_elements(
        By.CSS_SELECTOR,
        "#main .message-out",
    )
def ids_salientes(driver):
    result = set()
    for bubble in mensajes_salientes(driver):
        try:
            key = (
                bubble.get_attribute("data-id")
                or bubble.get_attribute("id")
            )
            if key:
                result.add(key)
        except StaleElementReferenceException:
            continue
    return result
def confirmar_mensaje(driver, previous_ids, message, require_image, previous_elements=None):
    """Confirma un mensaje saliente NUEVO por contenido y nodo DOM.

    WhatsApp puede omitir data-id y transformar saltos de línea / marcado.
    Nunca usa solo la desaparición del editor como prueba de envío.
    """
    expected = normalizar(message).replace("*", "").casefold()
    expected_compact = "".join(expected.split())
    if not expected_compact:
        return False
    old_elements = previous_elements or set()
    for bubble in reversed(mensajes_salientes(driver)[-60:]):
        try:
            key = bubble.get_attribute("data-id") or bubble.get_attribute("id")
            if key and key in previous_ids:
                continue
            # Si WhatsApp no expone identificador, exigimos un nodo nuevo.
            if not key and bubble.id in old_elements:
                continue
            raw = bubble.get_attribute("innerText") or bubble.text or ""
            actual = normalizar(raw).replace("*", "").casefold()
            actual_compact = "".join(actual.split())
            # La leyenda puede contener etiquetas adicionales de WhatsApp,
            # pero debe incluir el texto completo enviado en el mismo orden.
            if expected_compact not in actual_compact:
                continue
            # Un mensaje saliente nuevo con el texto exacto de la leyenda
            # confirma el reporte sin depender del DOM interno de la imagen.
            logger.info("Reporte nuevo confirmado por leyenda en historial.")
            return True
        except StaleElementReferenceException:
            continue
    return False

def enviar_imagen(
    driver,
    group_name,
    image_path,
    message,
    verify_history=True,
):
    logger.info(
        "PASO 6: Iniciando preparación de imagen."
    )
    verificar_destinatario(
        driver,
        group_name,
    )
    previous_ids = ids_salientes(driver)
    previous_elements = {bubble.id for bubble in mensajes_salientes(driver)}
    photo = preparar_imagen(
        image_path
    )
    logger.info(
        "PASO 7: Imagen preparada."
    )
    cargar_fotografia(
        driver,
        photo,
    )
    logger.info(
        "PASO 8: Imagen cargada en WhatsApp."
    )
    escribir_descripcion(
        driver,
        message,
    )
    logger.info(
        "PASO 9: Descripción escrita y verificada."
    )
    verificar_destinatario(
        driver,
        group_name,
    )
    logger.info(
        "PASO 10: Buscando botón de envío."
    )
    try:
        send_button = esperar(driver, 25).until(
            boton_enviar_imagen
        )
    except TimeoutException as exc:
        raise WhatsAppSendError(
            "No se encontró el botón de envío. "
            "No se realizó ningún clic."
        ) from exc
    logger.info(
        "PASO 11: Botón de envío encontrado."
    )
    verificar_destinatario(
        driver,
        group_name,
    )
    logger.info(
        "PASO 12: Enviando fotografía."
    )
    click_seguro(
        driver,
        send_button,
    )
    if not verify_history:
        # La cola NO inspecciona mensajes anteriores ni espera coincidencias
        # de texto en el historial. Solo espera a que WhatsApp cierre la vista
        # previa, dejando listo el chat para el siguiente archivo.
        logger.info("Esperando cierre del editor de foto antes del siguiente parque...")
        try:
            esperar(driver, 35).until(lambda d: not campo_descripcion(d))
        except TimeoutException as exc:
            raise WhatsAppSendError(
                "Se pulsó Enviar, pero el editor de fotografía no se cerró. "
                "Revisa el chat antes de reintentar este parque."
            ) from exc
        time.sleep(2)
        logger.info("Vista previa cerrada; continuando con el siguiente parque.")
        return True  # Clic procesado, NO confirmación de entrega.

    logger.info(
        "PASO 13: Verificando historial."
    )
    try:
        esperar(driver, 60).until(
            lambda d: confirmar_mensaje(
                d,
                previous_ids,
                message,
                True,
                previous_elements,
            )
        )
    except TimeoutException:
        logger.warning(
            "Se pulsó Enviar, pero WhatsApp no permitió confirmar el "
            "mensaje en el historial. Verifica el grupo antes de reintentar."
        )
        return False

    logger.info("PASO 14: Reporte confirmado en el historial.")
    return True
# ============================================================# ENVÍO SOLO TEXTO# ============================================================
def enviar_solo_texto(
    driver,
    group_name,
    message,
):
    verificar_destinatario(
        driver,
        group_name,
    )
    previous_ids = ids_salientes(driver)
    editor = esperar(driver, 30).until(
        editor_principal
    )
    escribir_multilinea(
        driver,
        editor,
        message,
    )
    verificar_destinatario(
        driver,
        group_name,
    )
    editor.send_keys(Keys.ENTER)
    esperar(driver, 45).until(
        lambda d: confirmar_mensaje(
            d,
            previous_ids,
            message,
            False,
        )
    )
# ============================================================# FUNCIÓN PRINCIPAL# ============================================================
def send_report(
    group_name,
    message,
    image_path=None,
    profile_dir=None,
    timeout=120,
):
    group_name = str(
        group_name or ""
    ).strip()
    message = str(
        message or ""
    )
    if not group_name:
        raise WhatsAppSendError(
            "Debes indicar el grupo."
        )
    if not message.strip():
        raise WhatsAppSendError(
            "El reporte CCTV está vacío."
        )
    if image_path and not Path(image_path).is_file():
        raise WhatsAppSendError(
            f"No existe la imagen: {image_path}"
        )
    if not SEND_LOCK.acquire(blocking=False):
        raise WhatsAppSendError(
            "Ya existe un envío en ejecución."
        )
    driver = None
    stage = "inicio"
    envio_posible = False
    try:
        logger.info(
            "Iniciando Google Chrome..."
        )
        profile = Path(
            profile_dir or PROFILE
        ).resolve()
        profile.mkdir(
            parents=True,
            exist_ok=True,
        )
        options = webdriver.ChromeOptions()
        options.add_argument(
            f"--user-data-dir={profile}"
        )
        options.add_argument(
            "--start-maximized"
        )
        options.add_argument(
            "--no-first-run"
        )
        options.add_argument(
            "--no-default-browser-check"
        )
        driver = webdriver.Chrome(
            options=options
        )
        stage = "whatsapp"
        logger.info(
            "Abriendo WhatsApp Web..."
        )
        driver.get(
            "https://web.whatsapp.com/"
        )
        esperar(driver, timeout).until(
            barra_busqueda
        )
        logger.info(
            "WhatsApp Web disponible."
        )
# ----------------------------------------------------# DIAGNÓSTICO DEL GRUPO# ----------------------------------------------------
        stage = "grupo"
        abrir_grupo(
            driver,
            group_name,
        )
        logger.info(
            "PASO 1: Grupo abierto."
        )
        verificar_destinatario(
            driver,
            group_name,
        )
        logger.info(
            "PASO 2: Destinatario verificado."
        )
        logger.info(
            "PASO 3: Buscando editor principal."
        )
        editor = esperar(driver, 30).until(
            editor_principal
        )
        logger.info(
            "PASO 4: Editor principal encontrado."
        )
        logger.info(
            "PASO 5: Continuando con el reporte."
        )
# ----------------------------------------------------# ENVÍO# ----------------------------------------------------
        if image_path:
            stage = "imagen_con_reporte"
            envio_posible = True
            confirmado = enviar_imagen(
                driver,
                group_name,
                image_path,
                message,
            )
            modalidad = "Fotografía con descripción"
        else:
            stage = "texto"
            envio_posible = True
            enviar_solo_texto(
                driver,
                group_name,
                message,
            )
            modalidad = "Solo texto"
        stage = "completado"
        logger.info("Automatización finalizada.")
        if image_path and not confirmado:
            return (
                f"Envío iniciado para «{group_name}», pero no se pudo "
                "confirmar en el historial. Revisa el chat antes de "
                "reintentar para evitar duplicados."
            )
        return (
            f"Reporte confirmado para «{group_name}».\n"
            f"Modalidad: {modalidad}"
        )
    except Exception as exc:
        logger.exception(
            "Error en etapa: %s",
            stage,
        )
        if driver is not None:
            guardar_diagnostico(
                driver,
                stage,
            )
        aviso = (
            "Revisa el historial antes de reintentar: "
            "el reporte podría haberse enviado."
            if envio_posible
            else "No se inició el envío."
        )
        raise WhatsAppSendError(
            f"Error en «{stage}»: {exc}. {aviso}"
        ) from exc
    finally:
        if driver is not None:
            logger.info(
                "Cerrando ChromeDriver..."
            )
            try:
                driver.quit()
            except WebDriverException:
                logger.warning(
                    "No se pudo cerrar ChromeDriver normalmente."
                )
        SEND_LOCK.release()


# ============================================================
# ENVÍO DE COLA: conserva el cargador original con pyautogui.
# ============================================================
def send_reports_batch(group_name, reports, on_progress=None, profile_dir=None, timeout=120):
    """Envía cada reporte con su imagen y texto en una sola sesión Chrome.

    Los reportes son dicts: park, message, image_path.
    No reintenta envíos inciertos. on_progress corre en el hilo llamador.
    """
    group_name = str(group_name or "").strip()
    items = list(reports)
    if not group_name or not items:
        raise WhatsAppSendError("Indica el grupo y al menos un reporte.")
    for item in items:
        if not str(item.get("park", "")).strip():
            raise WhatsAppSendError("Un reporte no tiene parque.")
        if not str(item.get("message", "")).strip():
            raise WhatsAppSendError(f"Reporte vacío: {item.get('park')}.")
        if not item.get("image_path") or not Path(item["image_path"]).is_file():
            raise WhatsAppSendError(f"Falta la imagen: {item.get('park')}.")
    if not SEND_LOCK.acquire(blocking=False):
        raise WhatsAppSendError("Ya existe un envío de WhatsApp en ejecución.")

    driver = None
    results = []
    def report(item, index, status, error=None):
        result = {"park": item["park"], "index": index, "status": status}
        if error is not None:
            result["error"] = str(error)
        results.append(result)
        if on_progress:
            try:
                on_progress(result)
            except Exception:
                logger.exception("No se pudo actualizar el progreso visual.")

    try:
        profile = Path(profile_dir or PROFILE).resolve()
        profile.mkdir(parents=True, exist_ok=True)
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={profile}")
        options.add_argument("--start-maximized")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        driver = webdriver.Chrome(options=options)
        driver.get("https://web.whatsapp.com/")
        esperar(driver, timeout).until(barra_busqueda)
        abrir_grupo(driver, group_name)
        verificar_destinatario(driver, group_name)

        for index, item in enumerate(items):
            try:
                # El método original usa el diálogo de Windows, no inputs de stickers.
                verificar_destinatario(driver, group_name)
                confirmado = enviar_imagen(
                    driver, group_name, item["image_path"], item["message"],
                    verify_history=False,
                )
                report(item, index, "procesado" if confirmado else "sin_confirmar")
                if not confirmado:
                    break
            except Exception as exc:
                logger.exception("Falló el reporte de %s", item["park"])
                if driver is not None:
                    try:
                        guardar_diagnostico(driver, f"lote_{index + 1}")
                    except Exception:
                        pass
                report(item, index, "sin_confirmar", exc)
                break

        for index in range(len(results), len(items)):
            report(items[index], index, "pendiente")

        # El cierre de la vista previa no significa que WhatsApp haya
        # terminado de subir la última fotografía a sus servidores.
        # Mantener Chrome abierto después del último clic de envío.
        if results and results[-1]["status"] == "procesado":
            logger.info(
                "Último reporte procesado. Manteniendo Chrome abierto "
                "20 segundos para permitir que termine la subida a WhatsApp..."
            )
            time.sleep(20)
            logger.info("Espera final completada; cerrando Chrome.")
        return results
    finally:
        if driver is not None:
            try:
                driver.quit()
            except WebDriverException:
                pass
        SEND_LOCK.release()
