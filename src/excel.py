"""
excel.py

Manejo del Excel Maestro y procesamiento del reporte diario de alarmas.
Basado strictly en día calendario (00:00 a 23:59).
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Union, Tuple
import re
import openpyxl
import pandas as pd


class ExcelManager:

    EQUIVALENCIAS_PARQUES = {
        "EL PELICANO": "El Pelicano",
        "RAUQUEN": "CL114 Rauquen",
        "CHILLAN 1": "CL121 Chillan I",
        "CHILLAN I": "CL121 Chillan I",
        "EL PASO": "CL126 El Paso",
        "MOLINA": "CL130 Molina",
        "VILLA ALEGRE": "CL125 Villa Alegre",
        "MUTUPIN": "CL129 Mutupin",
        "CHILLAN 2": "CL122 Chillan II",
        "CHILLAN II": "CL122 Chillan II",
        "VILLA CRUZ": "CL109 Villa Cruz",
        "PEGASUS": "CL124 Pegasus",
        "LEMU": "CL113 Lemu",
        "CARENA": "CL213 Carena",
        "ORION": "CL123 Orion",
        "PENCAHUE": "CL205 Pencahue",
        "SANTA CAROLINA": "CL132 Santa Carolina",
        "SANTA FE": "CL120 Santa Fe",
        "BATRES": "CL204 Batres",
        "PEQUEN": "CL209 Pequen",
        "LINARES": "CL127 Linares",
        "PACHIRA": "CL128 Pachira",
        "EL ROMERAL": "CL131 El Romeral",
        "BLB": "CL210 BLB",
        "VILLA SECA": "CL118 Villa Seca",
    }

    NOMBRE_HOJA_PLANTILLA = "PLANTILLA"

    # Días de la semana en inglés para coincidir con el diseño de la tabla
    DIAS_INGLES = ["Friday", "Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

    def __init__(self, archivo_maestro: Union[str, Path]):
        self.archivo_maestro = Path(archivo_maestro) if archivo_maestro else None

    def existe(self) -> bool:
        if not self.archivo_maestro:
            return False
        return self.archivo_maestro.exists()

    def _calcular_turno_y_fecha(self, dt: datetime):
        fecha = dt.date()
        hora = dt.time()
        t_inicio = datetime.strptime("08:00:00", "%H:%M:%S").time()
        t_fin = datetime.strptime("20:00:00", "%H:%M:%S").time()

        if t_inicio <= hora < t_fin:
            return fecha, "DAY"
        else:
            return fecha, "NIGHT"

    def procesar_reporte_alarmas(
        self, archivo_nuevo: Path
    ) -> Tuple[pd.DataFrame, int, datetime.date]:
        """Lee el archivo de alarmas contabilizando TODAS las alertas/eventos por parque y turno.

        Calcula el número de semana ISO en base al Lunes correspondiente,
        y devuelve también la fecha de inicio del ciclo (Viernes).
        """
        df = pd.read_excel(
            archivo_nuevo,
            sheet_name="Registro de alarmas y eventos",
            header=8,
        )

        col_hora = "Hora de activación (cliente)"
        col_region = "Región"

        df_filtrado = (
            df[[col_hora, col_region]].dropna(subset=[col_hora]).copy()
        )
        df_filtrado["dt"] = pd.to_datetime(df_filtrado[col_hora])

        def mapear_parque(val):
            if pd.isna(val):
                return None
            val_limpio = str(val).strip().upper()
            return self.EQUIVALENCIAS_PARQUES.get(val_limpio, str(val).strip())

        df_filtrado["Parque_Oficial"] = df_filtrado[col_region].apply(
            mapear_parque
        )
        df_filtrado = df_filtrado.dropna(subset=["Parque_Oficial"])

        turnos_fechas = df_filtrado["dt"].apply(self._calcular_turno_y_fecha)
        df_filtrado["Fecha_Reporte"] = [tf[0] for tf in turnos_fechas]
        df_filtrado["Turno"] = [tf[1] for tf in turnos_fechas]

        # ---------------------------------------------------------------------
        # CÁLCULO DE FECHA DE INICIO Y NÚMERO DE SEMANA
        # ---------------------------------------------------------------------
        fecha_min = df_filtrado["Fecha_Reporte"].min()
        fecha_dt = pd.to_datetime(fecha_min)

        # 1. Obtenemos el Lunes de esa misma semana para obtener el número WW oficial ISO
        lunes_semana = fecha_dt - pd.Timedelta(days=fecha_dt.dayofweek)
        iso_cal = lunes_semana.isocalendar()
        numero_semana = int(
            iso_cal.week if hasattr(iso_cal, "week") else iso_cal[1]
        )

        # 2. Obtenemos el Viernes de inicio para mapear las columnas de la tabla (Viernes a Jueves)
        dias_atras_viernes = (fecha_dt.dayofweek - 4) % 7
        viernes_inicio = (fecha_dt - pd.Timedelta(days=dias_atras_viernes)).date()
        # ---------------------------------------------------------------------

        conteo = (
            df_filtrado.groupby(["Fecha_Reporte", "Parque_Oficial", "Turno"])
            .size()
            .unstack(fill_value=0)
        )

        for col in ["DAY", "NIGHT"]:
            if col not in conteo.columns:
                conteo[col] = 0

        # Retorna los 3 valores que espera agregar_registros()
        return conteo.reset_index(), numero_semana, viernes_inicio

    def _preparar_encabezados_fechas(self, ws, viernes_inicio: datetime.date):
        """Escribe el rango semanal en B1 y formatea las columnas B-O en Fila 2

        siguiendo el estilo de la plantilla: 'Alarms on [Día] [Número Día] Day / Night'
        """
        jueves_cierre = viernes_inicio + timedelta(days=6)

        # 1. Rango de fecha en la Fila 1 (ej: 07-08-2026 to 13-08-2026)
        ws.cell(
            row=1,
            column=2,
            value=f"{viernes_inicio.strftime('%d-%m-%Y')} to {jueves_cierre.strftime('%d-%m-%Y')}",
        )

        # 2. Encabezados de días (Fila 2) desde Columna B (2) hasta O (15)
        col_actual = 2
        for i in range(7):
            fecha_dia = viernes_inicio + timedelta(days=i)
            nombre_dia = self.DIAS_INGLES[i]

            # Formato: "Alarms on Friday 14 Day / Night"
            texto_encabezado = f"Alarms on {nombre_dia} {fecha_dia.day} Day / Night"

            ws.cell(row=2, column=col_actual, value=texto_encabezado)
            col_actual += 2

    def agregar_registros(self, archivo_nuevo: Path, log_callback=None) -> dict:
        df_resumen, numero_semana, viernes_inicio = self.procesar_reporte_alarmas(
            archivo_nuevo
        )

        if df_resumen.empty:
            if log_callback:
                log_callback(
                    "WARNING: El reporte de alarmas no contiene registros válidos."
                )
            return {"total": 0, "agregados": 0, "omitidos": 0}

        wb = openpyxl.load_workbook(self.archivo_maestro)

        patron_hoja = re.compile(rf".*WW\s*0?{numero_semana}$", re.IGNORECASE)
        hoja_existente = None
        for sheetname in wb.sheetnames:
            if patron_hoja.match(sheetname):
                hoja_existente = sheetname
                break

        nombre_hoja_target = hoja_existente or f"Monitoreo WW {numero_semana:02d}"

        if hoja_existente:
            ws = wb[hoja_existente]
            if log_callback:
                log_callback(
                    f"EXCEL: Se actualizará la hoja existente '{hoja_existente}'"
                )
        else:
            if self.NOMBRE_HOJA_PLANTILLA in wb.sheetnames:
                hoja_base = wb[self.NOMBRE_HOJA_PLANTILLA]
            else:
                hoja_base = wb.worksheets[-1]

            ws = wb.copy_worksheet(hoja_base)
            ws.title = nombre_hoja_target

            # Escribir fechas dinámicas
            self._preparar_encabezados_fechas(ws, viernes_inicio)

            if log_callback:
                log_callback(
                    f"EXCEL: Se creó la hoja '{nombre_hoja_target}' desde la plantilla maestra."
                )

        # Identificar parques en la Columna A
        parques_maestro = {}
        fila_total_idx = None
        primera_fila_parque = None
        ultima_fila_parque = None

        for row_idx in range(3, ws.max_row + 1):
            val = ws.cell(row=row_idx, column=1).value
            if val is not None:
                val_str = str(val).strip()
                if val_str.upper() == "TOTAL":
                    fila_total_idx = row_idx
                elif val_str.upper() not in [
                    "PHOTOVOLTAIC PARK",
                    "FECHA",
                    "TURNO",
                    "",
                ]:
                    if primera_fila_parque is None:
                        primera_fila_parque = row_idx
                    ultima_fila_parque = row_idx
                    parques_maestro[val_str.upper()] = row_idx

        fechas_procesadas = df_resumen["Fecha_Reporte"].unique()
        registros_agregados = 0

        for fecha in fechas_procesadas:
            df_fecha = df_resumen[df_resumen["Fecha_Reporte"] == fecha]

            # Calcular la columna B-O según la diferencia de días respecto al Viernes de inicio
            dias_diferencia = (fecha - viernes_inicio).days

            if 0 <= dias_diferencia <= 6:
                col_day_idx = 2 + (dias_diferencia * 2)
                col_night_idx = col_day_idx + 1
            else:
                continue  # Fuera del rango de la semana

            map_day = {
                str(k).strip().upper(): v
                for k, v in zip(df_fecha["Parque_Oficial"], df_fecha["DAY"])
            }
            map_night = {
                str(k).strip().upper(): v
                for k, v in zip(df_fecha["Parque_Oficial"], df_fecha["NIGHT"])
            }

            # Escribir en la matriz fija
            for parque_nombre, row_idx in parques_maestro.items():
                cant_day = map_day.get(parque_nombre, 0)
                cant_night = map_night.get(parque_nombre, 0)

                ws.cell(row=row_idx, column=col_day_idx, value=int(cant_day))
                ws.cell(row=row_idx, column=col_night_idx, value=int(cant_night))
                if cant_day > 0 or cant_night > 0:
                    registros_agregados += 1

            # Mantener fórmulas de SUMA en fila TOTAL
            if fila_total_idx and primera_fila_parque and ultima_fila_parque:
                for col_idx in [col_day_idx, col_night_idx]:
                    letra_col = openpyxl.utils.get_column_letter(col_idx)
                    ws.cell(
                        row=fila_total_idx,
                        column=col_idx,
                        value=f"=SUM({letra_col}{primera_fila_parque}:{letra_col}{ultima_fila_parque})",
                    )

        wb.save(self.archivo_maestro)

        total_leidos = len(df_resumen)
        return {
            "total": total_leidos,
            "agregados": registros_agregados,
            "omitidos": max(0, total_leidos - registros_agregados),
        }