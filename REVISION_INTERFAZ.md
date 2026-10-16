# NovaCommand CCTV — actualización visual

## Alcance
- Encabezado más claro con jerarquía de marca y subtítulo contextual.
- Barra lateral con navegación más espaciosa y selección destacada.
- Tarjetas y panel de reportes semanales con radios y espaciados consistentes.
- Formulario CCTV con títulos más claros, nueva paleta coordinada y botones de cola más visibles.
- Se conservan el método de imágenes de la v1.0.6, la lógica de WhatsApp, la importación de Excel y el instalador.

## Verificaciones
- Compilación de sintaxis Python: correcta.
- Pruebas de UI y regresión estática: ejecutar `py -m pytest -q tests/test_ui_refresh.py`.
- Suite completa: requiere dependencias de `requirements.txt` y entorno Windows para las pruebas visuales y WhatsApp. En este entorno faltó `customtkinter`, por lo que una prueba dinámica no pudo ejecutarse.

## Checklist Windows antes del lanzamiento
1. Ejecutar `py -m pip install -r requirements.txt` y `py -m pytest -v tests/`.
2. Abrir configuración inicial, navegar entre ambos módulos y comprobar ícono y logo.
3. Adjuntar primera imagen, agregar a cola, adjuntar segunda imagen distinta y comprobar que no reaparezca `pyimage`.
4. Enviar dos reportes al grupo de prueba en español y en inglés; verificar que llegan ambos y que Chrome espera al final.
5. Importar Excel de prueba, volver a importarlo y comprobar actualización, respaldo y ausencia de duplicados.
6. Compilar con GitHub Actions, instalar en Windows y repetir pasos 2 a 5 desde el ejecutable.
