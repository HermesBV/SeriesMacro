import os
import unittest

import pandas as pd

import view_iiep
from view_mapa_datos import _bubble_html


def inventario():
    filas = [
        ("iiep-rin", "rin-netas-m", "Reservas internacionales netas", "IIEP Reservas M", "Reservas netas"),
        ("iiep-rin", "rin-brutas-m", "Reservas internacionales brutas", "IIEP Reservas M", "Reservas brutas"),
        ("iiep", "itcrb-eeuu-empalmado-importacion-m", "ITCRB Estados Unidos (mensual)", "IIEP ITCRB EEUU M", "ITCRB"),
        ("bcra-dmd", "246", "Reservas internacionales", "BCRA D", "Reservas"),
    ]
    df = pd.DataFrame(filas, columns=["Código fuente", "ID", "Nombre serie", "Pestaña", "Columna BD"])
    df["_Clave"] = df["Código fuente"] + "::" + df["ID"]
    return df


class IndicadoresIIEPTests(unittest.TestCase):
    def setUp(self):
        self.grupos = view_iiep.GRUPOS_POR_CLAVE

    def test_cada_grupo_toma_solo_sus_series_en_su_orden(self):
        reservas = view_iiep.series_del_grupo(self.grupos["reservas"], inventario())
        itcrb = view_iiep.series_del_grupo(self.grupos["itcrb"], inventario())
        self.assertEqual(reservas["ID"].tolist(), ["rin-brutas-m", "rin-netas-m"])
        self.assertEqual(reservas["Etiqueta"].tolist(), ["Brutas", "Netas"])
        self.assertEqual(itcrb["ID"].tolist(), ["itcrb-eeuu-empalmado-importacion-m"])

    def test_etiquetas_repetidas_se_distinguen_por_id(self):
        df = inventario()
        extra = df.iloc[[0]].assign(ID="rin-otra-m", **{"Nombre serie": "Netas"})
        df = pd.concat([df, extra, extra.assign(ID="rin-otra2-m")], ignore_index=True)
        filas = view_iiep.series_del_grupo(self.grupos["reservas"], df)
        self.assertEqual(filas["Etiqueta"].nunique(), len(filas))

    def test_resumen_muestra_ultimo_dato_y_mismo_mes_del_anio_anterior(self):
        fechas = pd.date_range("2025-07-01", "2026-08-01", freq="MS")
        hoja = pd.DataFrame({"fecha": fechas, "Reservas brutas": range(len(fechas))})
        filas = view_iiep.series_del_grupo(self.grupos["reservas"], inventario()).iloc[[0]]
        tabla = view_iiep.tabla_valores(filas, {"IIEP Reservas M": hoja})
        resumen = view_iiep.resumen_ultimos(tabla)
        self.assertEqual(resumen.loc[0, "Serie"], "Brutas")
        self.assertEqual(resumen.loc[0, "Fecha"], pd.Timestamp("2026-08-01"))
        self.assertEqual(resumen.loc[0, "Valor"], len(fechas) - 1)
        self.assertEqual(resumen.loc[0, "Un año antes"], len(fechas) - 13)

    def test_formato_numerico_y_fechas(self):
        self.assertEqual(view_iiep.numero(46091.725), "46.091,7")
        self.assertEqual(view_iiep.numero(-2451.86), "−2.451,9")
        self.assertEqual(view_iiep.numero(-0.04), "0,0")
        self.assertEqual(view_iiep.numero(None), "s/d")
        self.assertEqual(view_iiep.mes_anio(pd.Timestamp("2026-09-01")), "sep-2026")
        self.assertEqual(view_iiep.mes_anio(pd.NaT), "s/d")
        self.assertEqual(view_iiep.unidad_corta(float("nan")), "")
        self.assertEqual(view_iiep.unidad_corta("Millones de dólares estadounidenses"), "M USD")

    def test_periodo_tolera_inventario_sin_fechas(self):
        filas = inventario().iloc[:2]
        self.assertEqual(view_iiep.periodo_y_frecuencia(filas), "2 series")
        con_fechas = filas.assign(Frecuencia="Mensual", **{"Fecha inicio": ["2000-09-01", None],
                                                          "Fecha fin": [None, None]})
        self.assertEqual(view_iiep.periodo_y_frecuencia(con_fechas), "2 series mensuales")

    def test_recorte_por_periodo_cuenta_desde_el_ultimo_dato(self):
        fechas = pd.date_range("2000-01-01", "2026-09-01", freq="MS")
        tabla = pd.DataFrame({"Brutas": range(len(fechas))}, index=fechas)
        self.assertEqual(view_iiep.recortar(tabla, 5).index.min(), pd.Timestamp("2021-09-01"))
        self.assertEqual(len(view_iiep.recortar(tabla, None)), len(tabla))

    def test_los_anexos_declarados_existen(self):
        for grupo in view_iiep.GRUPOS:
            for _, ruta in grupo.anexos:
                self.assertTrue(os.path.exists(ruta), ruta)


class MapaBurbujasTests(unittest.TestCase):
    def test_burbujas_con_punto_de_miles_y_sin_clasificar_gris(self):
        html = _bubble_html(pd.DataFrame({"Tema": ["Actividad", "Sin clasificar"], "Series": [5273, 12]}))
        self.assertIn("5.273 series", html)
        self.assertIn("--color:#5F6B73", html)
        self.assertEqual(html.count('class="topic-bubble"'), 2)


if __name__ == "__main__":
    unittest.main()
