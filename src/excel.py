"""
excel.py

Manejo del Excel Maestro y procesamiento del reporte diario de alarmas por semana (WW).
Conserva fórmulas nativas =SUM(...) en las filas de TOTAL.
"""

from datetime import datetime, timedelta
from pathlib import Path
import openpyxl
import pandas as pd


class ExcelManager:

    # Mapeo de equivalencias: Nombre en Reporte -> Nombre Oficial Maestro
    EQUIVALENCIAS_PARQUES = {
        "EL PELICANO": "El Pelicano",
        "RAUQUEN": "CL114 Rauquen",
        "CHILLAN 1": "Chillan 1",
        "EL PASO": "CL126 El Paso",
        "MOLINA": "CL130 Molina",
        "VILLA ALEGRE": "CL125 Villa Alegre",
        "MUTUPIN": "CL129 Mutupin",
        "CHILLAN 2": "Chillan 2",
        "VILLA CRUZ": "CL109 Villa Cruz",
        "PEGASUS": "Pegasus",
        "LEMU": "CL113 Lemu",
        "CARENA": "Carena",
        "ORION": "Orion",
        "PENCAHUE": "Pencahue",
        "SANTA CAROLINA": "CL132 Santa Carolina",
        "SANTA FE": "CL120 Santa Fe",
        "BATRES": "Batres",
        "PEQUEN": "Pequen",
        "LINARES": "Linares",
        "PACHIRA": "Pachira",
        "EL ROMERAL": "CL131 El Romeral",
        "BLB": "BLB",
    }

    def __init__(self, archivo_maestro: Path):
        self.archivo_maestro = archivo_maestro

    def existe(self):
        return self.archivo_maestro.exists()

    def _calcular_turno_y_fecha(self, dt: datetime):
        """
        Calcula el turno y la fecha objetivo del reporte:
        - 08:00:00 a 19:59:59 -> DAY del mismo día.
        - 20:00:00 a 23:59:59 -> NIGHT del DÍA SIGUIENTE.
        - 00:00:00 a 07:59:59 -> NIGHT del mismo día.
        """
        hora = dt.time()
        t_inicio_dia = datetime.strptime("08:00:00", "%H:%M:%S").time()
        t_fin_dia = datetime.strptime("19:59:59", "%H:%M:%S").time()

        if t_inicio_dia <= hora <= t_fin_dia:
            turno = "DAY"
            fecha_reporte = dt.date()
        elif dt.hour >= 20:
            turno = "NIGHT"
            fecha_reporte = (dt + timedelta(days=1)).date()
        else:
            turno = "NIGHT"
            fecha_reporte = dt.date()

        return fecha_reporte, turno

    def procesar_reporte_alarmas(self, archivo_nuevo: Path) -> tuple[pd.DataFrame, str]:
        """
        Lee 'Registro de alarmas y eventos' desde la fila 10,
        mapea parques, calcula la semana del año (WW) y agrupa el conteo por Fecha, Parque y Turno.
        """
        df = pd.read_excel(
            archivo_nuevo,
            sheet_name="Registro de alarmas y eventos",
            skiprows=9
        )

        col_hora = df.columns[4]    # Columna E (Hora)
        col_region = df.columns[6]  # Columna G (Región)

        df_filtrado = df[[col_hora, col_region]].dropna(subset=[col_hora]).copy()
        df_filtrado["dt"] = pd.to_datetime(df_filtrado[col_hora])

        def mapear_parque(val):
            if pd.isna(val):
                return None
            val_limpio = str(val).strip().upper()
            return self.EQUIVALENCIAS_PARQUES.get(val_limpio, str(val).strip())

        df_filtrado["Parque_Oficial"] = df_filtrado[col_region].apply(mapear_parque)
        df_filtrado = df_filtrado.dropna(subset=["Parque_Oficial"])

        turnos_fechas = df_filtrado["dt"].apply(self._calcular_turno_y_fecha)
        df_filtrado["Fecha_Reporte"] = [tf[0] for tf in turnos_fechas]
        df_filtrado["Turno"] = [tf[1] for tf in turnos_fechas]

        # Determinar número de semana ISO (ej. WW 33)
        primera_fecha = df_filtrado["Fecha_Reporte"].min()
        numero_semana = primera_fecha.isocalendar()[1]
        nombre_hoja_target = f"Monitoreo WW {numero_semana:02d}"

        conteo = df_filtrado.groupby(
            ["Fecha_Reporte", "Parque_Oficial", "Turno"]
        ).size().unstack(fill_value=0)

        for col in ["DAY", "NIGHT"]:
            if col not in conteo.columns:
                conteo[col] = 0

        return conteo.reset_index(), nombre_hoja_target

    def agregar_registros(self, archivo_nuevo: Path) -> int:
        """
        Procesa el reporte de alarmas, abre o clona la hoja 'Monitoreo WW XX'
        preservando el diseño y las fórmulas =SUM(...) en los Totales.
        """
        df_resumen, nombre_hoja_target = self.procesar_reporte_alarmas(archivo_nuevo)

        if df_resumen.empty:
            return 0

        wb = openpyxl.load_workbook(self.archivo_maestro)

        # 1. Verificar o Clonar la Hoja Base
        if nombre_hoja_target in wb.sheetnames:
            ws = wb[nombre_hoja_target]
        else:
            # Clona la última o primera hoja conservando todos los estilos y formatos
            hoja_base = wb.worksheets[-1]
            ws = wb.copy_worksheet(hoja_base)
            ws.title = nombre_hoja_target

        # 2. Identificar parques y la fila TOTAL
        parques_maestro = []
        fila_total_idx = None
        primera_fila_parque = None
        ultima_fila_parque = None

        for row_idx in range(2, ws.max_row + 1):
            val = ws.cell(row=row_idx, column=1).value
            if val is not None:
                val_str = str(val).strip()
                if val_str.upper() == "TOTAL":
                    fila_total_idx = row_idx
                    break
                if primera_fila_parque is None:
                    primera_fila_parque = row_idx
                ultima_fila_parque = row_idx
                parques_maestro.append((row_idx, val_str))

        # 3. Procesar fechas del reporte
        fechas_procesadas = df_resumen["Fecha_Reporte"].unique()
        total_filas_actualizadas = 0

        for fecha in fechas_procesadas:
            df_fecha = df_resumen[df_resumen["Fecha_Reporte"] == fecha]
            str_fecha = fecha.strftime("%d %b")

            col_day_idx = None
            col_night_idx = None

            # Buscar si la fecha ya existe en los encabezados
            for col_idx in range(2, ws.max_column + 1):
                val_header = ws.cell(row=1, column=col_idx).value
                val_sub = ws.cell(row=2, column=col_idx).value
                
                header_str = str(val_header).strip() if val_header else ""
                sub_str = str(val_sub).strip().upper() if val_sub else ""

                if str_fecha.lower() in header_str.lower():
                    if sub_str == "DAY":
                        col_day_idx = col_idx
                    elif sub_str == "NIGHT":
                        col_night_idx = col_idx

            # Crear columnas si no existen
            if not col_day_idx or not col_night_idx:
                col_base = ws.max_column + 1 if ws.cell(row=1, column=ws.max_column).value else ws.max_column
                
                col_day_idx = col_base
                ws.cell(row=1, column=col_day_idx, value=str_fecha)
                ws.cell(row=2, column=col_day_idx, value="DAY")

                col_night_idx = col_base + 1
                ws.cell(row=1, column=col_night_idx, value=str_fecha)
                ws.cell(row=2, column=col_night_idx, value="NIGHT")

            map_day = dict(zip(df_fecha["Parque_Oficial"], df_fecha["DAY"]))
            map_night = dict(zip(df_fecha["Parque_Oficial"], df_fecha["NIGHT"]))

            # Escribir registros en las filas de los parques
            for row_idx, parque in parques_maestro:
                cant_day = map_day.get(parque, 0)
                cant_night = map_night.get(parque, 0)

                ws.cell(row=row_idx, column=col_day_idx, value=int(cant_day))
                ws.cell(row=row_idx, column=col_night_idx, value=int(cant_night))
                total_filas_actualizadas += 1

            # 4. Manejo Inteligente del TOTAL (Fórmulas Excel)
            if fila_total_idx and primera_fila_parque and ultima_fila_parque:
                for col_idx in [col_day_idx, col_night_idx]:
                    celda_total = ws.cell(row=fila_total_idx, column=col_idx)
                    val_actual = str(celda_total.value or "")

                    # Si la celda no contiene una fórmula '=', asignamos la fórmula =SUM(...)
                    if not val_actual.startswith("="):
                        letra_col = openpyxl.utils.get_column_letter(col_idx)
                        celda_total.value = f"=SUM({letra_col}{primera_fila_parque}:{letra_col}{ultima_fila_parque})"

        wb.save(self.archivo_maestro)
        return total_filas_actualizadas