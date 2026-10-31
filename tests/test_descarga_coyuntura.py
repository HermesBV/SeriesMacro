import unittest

import utils


class ClaveCoyunturaTests(unittest.TestCase):
    def test_acepta_variantes_de_la_clave(self):
        for texto in ("abrete sesamo", "Ábrete Sésamo", "  abrete   sesamo ", "ABRETE SESAMO"):
            self.assertTrue(utils.pide_coyuntura(texto), texto)

    def test_rechaza_otros_textos(self):
        for texto in ("", None, "abrete", "abrete sesamo ya", "PIB"):
            self.assertFalse(utils.pide_coyuntura(texto), repr(texto))


if __name__ == "__main__":
    unittest.main()
