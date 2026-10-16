# NovaCommand CCTV 1.0.0

## Crear el instalador

### GitHub Actions (recomendado)
Sube este proyecto a tu repositorio GitHub, abre **Actions > NovaCommand CCTV - Instalador Windows > Run workflow**. Cuando finalice, descarga el artefacto `NovaCommand-CCTV-Setup-v1.0.0`, descomprímelo y ejecuta el instalador `.exe`.

### Windows local
Instala Python 3.11 e Inno Setup 6. En PowerShell, desde la carpeta del proyecto, ejecuta `./COMPILAR_INSTALADOR_WINDOWS.ps1`.

## Datos de usuario
Las configuraciones y capturas se guardan en `%LOCALAPPDATA%\NovaCommand CCTV` al usar el ejecutable. El perfil existente de WhatsApp se conserva en `%LOCALAPPDATA%\WeeklyReportCFC\ChromeWhatsApp`, para mantener la sesión anterior.

## Precauciones
La compilación debe ejecutarse en Windows. El envío de WhatsApp usa automatización de Chrome y puede requerir interacción con el selector de archivos; no usar mouse ni teclado durante la tanda. El último mensaje dispone de 20 segundos de espera antes de cerrar Chrome, sin garantía de entrega. Verifica el envío con el grupo de pruebas antes de uso operativo.
