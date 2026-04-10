from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from meshrender_studio.figure_layout import compose_zoom_inset


class FigureLayoutTests(unittest.TestCase):
    def test_compose_zoom_inset_draws_crop_and_inset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "figure.png"
            image = Image.new("RGB", (100, 100), "white")
            for x in range(100):
                for y in range(100):
                    if x < 50 and y < 50:
                        color = (255, 0, 0)
                    elif x >= 50 and y < 50:
                        color = (0, 255, 0)
                    elif x < 50 and y >= 50:
                        color = (0, 0, 255)
                    else:
                        color = (255, 255, 0)
                    image.putpixel((x, y), color)
            image.save(image_path)

            compose_zoom_inset(
                image_path,
                {
                    "crop_box": [0.1, 0.6, 0.2, 0.2],
                    "inset_box": [0.55, 0.1, 0.3, 0.3],
                    "stroke_color": [0.95, 0.43, 0.16],
                    "stroke_width": 4,
                },
            )

            composed = Image.open(image_path)
            self.assertEqual(composed.getpixel((70, 25)), (0, 0, 255))
            self.assertEqual(composed.getpixel((10, 60)), (242, 110, 41))


if __name__ == "__main__":
    unittest.main()
