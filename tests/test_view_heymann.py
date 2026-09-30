import io
import unittest

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image

from view_heymann import plot_heymann_camel


class HeymannChartTests(unittest.TestCase):
    def test_png_tiene_fondo_blanco_opaco(self):
        dates = pd.date_range("2025-01-01", periods=18, freq="MS")
        values = [90, 92, 95, 94, 97, 101, 99, 103, 105,
                  104, 107, 108, 110, 109, 111, 114, 112, 116]
        fig = plot_heymann_camel(pd.DataFrame({"fecha": dates, "valor": values}))
        self.assertIsNotNone(fig)
        output = io.BytesIO()
        try:
            fig.savefig(output, format="png", transparent=False, facecolor="white",
                        bbox_inches="tight")
            image = Image.open(output).convert("RGBA")
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255, 255))
        finally:
            plt.close(fig)


if __name__ == "__main__":
    unittest.main()
