"""Flujos de navegación de la app completa con la base publicada (bds/).

Cargan la base real, por lo que tardan alrededor de un minuto.
"""
import os
import unittest

from streamlit.testing.v1 import AppTest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app(**parametros):
    os.chdir(RAIZ)
    prueba = AppTest.from_file("main.py", default_timeout=600)
    for clave, valor in parametros.items():
        prueba.query_params[clave] = valor
    return prueba.run()


def boton(prueba, clave):
    return next(b for b in prueba.button if b.key == clave)


@unittest.skipUnless(os.path.exists(os.path.join(RAIZ, "bds", "BD.xlsx")), "falta la base publicada")
class FlujosIndicadoresIIEPTests(unittest.TestCase):
    def test_enlace_directo_abre_el_grupo_con_las_destacadas(self):
        prueba = app(vista="iiep", grupo="reservas")
        self.assertFalse(prueba.exception)
        self.assertEqual(prueba.button_group[0].value, ["Brutas", "Netas", "Líquidas"])

    def test_volver_y_salir_de_la_vista_dejan_el_mosaico(self):
        prueba = app(vista="iiep", grupo="reservas")
        boton(prueba, "iiep_volver").click().run()
        self.assertNotIn("grupo", prueba.query_params)
        self.assertTrue(any(b.key == "iiep_abrir_reservas" for b in prueba.button))

        boton(prueba, "iiep_abrir_reservas").click().run()
        self.assertEqual(prueba.query_params["grupo"], ["reservas"])
        boton(prueba, "nav_macro").click().run()
        self.assertNotIn("grupo", prueba.query_params)
        boton(prueba, "nav_iiep").click().run()
        self.assertTrue(any(b.key == "iiep_abrir_reservas" for b in prueba.button))
        self.assertFalse(prueba.exception)

    def test_seleccion_vacia_y_seleccion_conservada(self):
        prueba = app(vista="iiep", grupo="reservas")
        prueba.button_group[0].set_value([]).run()
        self.assertFalse(prueba.exception)
        self.assertTrue(any("al menos una serie" in info.value for info in prueba.info))
        prueba.button_group[0].set_value(["Custodia"]).run()
        boton(prueba, "nav_map").click().run()
        boton(prueba, "nav_iiep").click().run()
        boton(prueba, "iiep_abrir_reservas").click().run()
        self.assertEqual(prueba.button_group[0].value, ["Custodia"])
        self.assertFalse(prueba.warning)

    def test_parametros_invalidos_no_rompen_ni_quedan_en_la_url(self):
        prueba = app(vista="iiep", grupo="zzz")
        self.assertFalse(prueba.exception)
        self.assertNotIn("grupo", prueba.query_params)
        prueba = app(vista="foo", grupo="reservas")
        self.assertFalse(prueba.exception)
        self.assertNotIn("vista", prueba.query_params)
        self.assertNotIn("grupo", prueba.query_params)


if __name__ == "__main__":
    unittest.main()
