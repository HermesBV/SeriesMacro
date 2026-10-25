import unittest

import pandas as pd

import view_iiep


def inventario():
    filas = [
        ("iiep-rin", "rin-brutas-m", "Reservas internacionales brutas", "IIEP Reservas M", "Reservas brutas"),
        ("iiep-rin", "rin-netas-m", "Reservas internacionales netas", "IIEP Reservas M", "Reservas netas"),
        ("iiep", "itcrb-eeuu-empalmado-importacion-m", "ITCRB Estados Unidos (mensual)", "IIEP ITCRB EEUU M", "ITCRB"),
        ("bcra-dmd", "246", "Reservas internacionales", "BCRA D", "Reservas"),
    ]
    df = pd.DataFrame(filas, columns=["Código fuente", "ID", "Nombre serie", "Pestaña", "Columna BD"])
    df["_Clave"] = df["Código fuente"] + "::" + df["ID"]
    return df


class IndicadoresIIEPTests(unittest.TestCase):
    def test_cada_grupo_toma_solo_sus_series(self):
        grupos = {grupo.clave: grupo for grupo in view_iiep.GRUPOS}
        reservas = view_iiep.series_del_grupo(grupos["reservas"], inventario())
        itcrb = view_iiep.series_del_grupo(grupos["itcrb"], inventario())
        self.assertEqual(reservas["ID"].tolist(), ["rin-brutas-m", "rin-netas-m"])
        self.assertEqual(itcrb["ID"].tolist(), ["itcrb-eeuu-empalmado-importacion-m"])

    def test_resumen_muestra_ultimo_dato_y_mismo_mes_del_anio_anterior(self):
        fechas = pd.date_range("2025-07-01", "2026-08-01", freq="MS")
        hoja = pd.DataFrame({"fecha": fechas, "Reservas brutas": range(len(fechas))})
        filas = inventario().iloc[[0]]
        tabla = view_iiep.tabla_valores(filas, {"IIEP Reservas M": hoja})
        resumen = view_iiep.resumen_ultimos(tabla)
        self.assertEqual(resumen.loc[0, "Último dato"], "2026-08")
        self.assertEqual(resumen.loc[0, "Valor"], len(fechas) - 1)
        self.assertEqual(resumen.loc[0, "Un año antes"], len(fechas) - 13)

    def test_los_anexos_declarados_existen(self):
        import os
        for grupo in view_iiep.GRUPOS:
            for _, ruta in grupo.anexos:
                self.assertTrue(os.path.exists(ruta), ruta)


if __name__ == "__main__":
    unittest.main()
