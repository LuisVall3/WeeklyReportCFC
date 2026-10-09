

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

8. Verificar el historial.

Dependencias:

    py -m pip install selenium pillow

"""

from pathlib import Path

from datetime import datetime

import logging

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

ROOT = Path(__file__).resolve().parent.parent

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



    # WhatsApp Web usa el idioma configurado en el equipo.
    # En el PC de operaciones aparece «Fotos y videos», no «Photos & videos».
    def opcion_fotos(d):
        for item in d.find_elements(By.CSS_SELECTOR, '[role="menuitem"]'):
            try:
                if not item.is_displayed() or not item.is_enabled():
                    continue
                texto = normalizar((item.get_attribute("aria-label") or "") + " " + (item.text or "")).casefold()
                if "photos & videos" in texto or "fotos y videos" in texto or "fotos e vídeos" in texto:
                    return item
            except StaleElementReferenceException:
                continue
        return False

    try:
        opcion = esperar(driver, 15).until(opcion_fotos)
    except TimeoutException as exc:
        raise WhatsAppSendError(
            "No se encontró la opción Fotos y videos del menú de adjuntos "
            "(idioma o estructura de WhatsApp Web). No se envió ningún mensaje."
        ) from exc

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

    """Encuentra exclusivamente el botón de envío de la vista previa de foto."""

    if not campo_descripcion(driver):

        return False

    botones = driver.find_elements(

        By.CSS_SELECTOR,

        '[role="button"][aria-label^="Send "]:has([data-icon="wds-ic-send-filled"])'

    )

    candidatos = []

    for boton in botones:

        try:

            if boton.is_displayed() and boton.is_enabled():

                candidatos.append(boton)

        except StaleElementReferenceException:

            continue

    if len(candidatos) != 1:

        logger.info('Botones de envío de foto encontrados: %s', len(candidatos))

        return False

    logger.info('Botón de envío identificado: %s', candidatos[0].get_attribute('aria-label'))

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

def confirmar_mensaje(driver, previous_ids, message, require_image):

    """

    Confirma únicamente mensajes salientes nuevos, posteriores al clic.

    No exige que WhatsApp exponga la imagen mediante una etiqueta img.

    """

    expected = normalizar(message).replace("*", "")

    # WhatsApp convierte el Markdown en texto visual, sin asteriscos.

    expected_lines = [

        normalizar(line).replace("*", "")

        for line in message.splitlines()

        if normalizar(line)

    ]



    for bubble in reversed(mensajes_salientes(driver)[-50:]):

        try:

            key = bubble.get_attribute("data-id") or bubble.get_attribute("id")

            if key and key in previous_ids:

                continue



            text = normalizar(

                bubble.get_attribute("innerText") or bubble.text or ""

            ).replace("*", "")



            if not text or not all(line in text for line in expected_lines):

                continue



            if require_image:

                # Señales multimedia amplias, sin depender de un solo testid.

                media = bubble.find_elements(

                    By.CSS_SELECTOR,

                    'img, video, canvas, [data-testid*="media"], '

                    '[data-testid*="image"], [data-icon*="image"], '

                    '[style*="background-image"]'

                )

                if not media:

                    continue



            logger.info("Reporte nuevo encontrado en historial de salientes.")

            return True

        except StaleElementReferenceException:

            continue



    return False



def enviar_imagen(

    driver,

    group_name,

    image_path,

    message,

):

    logger.info(

        "PASO 6: Iniciando preparación de imagen."

    )

    verificar_destinatario(

        driver,

        group_name,

    )

    previous_ids = ids_salientes(driver)

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
