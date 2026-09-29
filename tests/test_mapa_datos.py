import unittest

import pandas as pd

from view_mapa_datos import _branch_html, hierarchy_nodes
from utils import TOPICS, normalize_topic


class MapaDatosTests(unittest.TestCase):
    def test_ultimo_nivel_no_es_desplegable(self):
        rows = pd.DataFrame([
            {"Institución": "INDEC", "Área": "Sociedad", "Subárea 1": "Trabajo",
             "Subárea 2": "Ingresos", "Subárea 3": "Sin mayor detalle"},
            {"Institución": "INDEC", "Área": "Sociedad", "Subárea 1": "Trabajo",
             "Subárea 2": "Ingresos", "Subárea 3": "Sin mayor detalle"},
        ])
        nodes = hierarchy_nodes(rows)
        last = nodes.loc[nodes["label"].eq("Ingresos")].iloc[0]
        self.assertEqual(last["count"], 2)
        self.assertFalse(nodes["label"].eq("Sin mayor detalle").any())
        html = _branch_html(nodes)
        self.assertIn('class="tree-leaf"><span class="tree-name">Ingresos</span>', html)
        self.assertNotIn('class="tree-name">Ingresos</span><span class="tree-count">2 series</span><span class="tree-expand"', html)

    def test_temas_existentes_absorben_variantes(self):
        self.assertEqual(len(TOPICS), 8)
        self.assertEqual(normalize_topic("Trabajo"), "Trabajo e ingresos")
        self.assertEqual(normalize_topic("Salarios"), "Trabajo e ingresos")
        self.assertEqual(normalize_topic("Riesgo país"), "Mercados financieros")
        with self.assertRaisesRegex(ValueError, "Tema no reconocido"):
            normalize_topic("Tema nuevo")


if __name__ == "__main__":
    unittest.main()
