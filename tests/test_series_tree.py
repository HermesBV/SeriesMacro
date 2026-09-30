import unittest

import pandas as pd

from series_tree import next_groups, series_path


class SeriesTreeTests(unittest.TestCase):
    def test_ruta_ipc_y_grupos_directos(self):
        rows = pd.DataFrame([
            {"Institución": "INDEC", "Área": "Economía", "Subárea 1": "Precios",
             "Subárea 2": "IPC", "Subárea 3": "Sin mayor detalle",
             "Archivo origen": "latest.xls", "Grupo de hojas": "IPC cobertura nacional",
             "Hoja origen": sheet, "Grupo de series 1": "Región Cuyo"}
            for sheet in ("Índices IPC Cobertura Nacional", "Variación mensual IPC Nacional")
        ])
        self.assertEqual(series_path(rows.iloc[0]), (
            "INDEC", "Economía", "Precios", "IPC", "latest.xls", "IPC cobertura nacional",
            "Índices IPC Cobertura Nacional", "Región Cuyo",
        ))
        self.assertEqual(next_groups(rows, ("INDEC", "Economía", "Precios", "IPC")),
                         [("latest.xls", 2)])
        self.assertEqual(len(next_groups(rows, series_path(rows.iloc[0]))), 0)

    def test_navegacion_y_seleccion_en_streamlit(self):
        from streamlit.testing.v1 import AppTest

        def app():
            import pandas as pd
            import streamlit as st
            import series_tree

            if "selected_ids" not in st.session_state:
                st.session_state["selected_ids"] = set()
            series_tree.show(pd.DataFrame([{
                "Instituci\u00f3n": "INDEC", "\u00c1rea": "Precios", "_Clave": "indec|ipc",
                "Nombre serie": "IPC", "Frecuencia": "Mensual", "Unidad": "\u00cdndice", "ID": "ipc",
            }]))

        page = AppTest.from_function(app, default_timeout=15).run()
        self.assertEqual(len(page.exception), 0)
        page.button[0].click().run()  # Institución
        page.button[1].click().run()  # Área
        self.assertEqual(len(page.exception), 0)
        self.assertIn("IPC", page.button[1].label)
        page.button[1].click().run()  # Serie
        self.assertEqual(page.session_state["selected_ids"], {"indec|ipc"})


if __name__ == "__main__":
    unittest.main()
