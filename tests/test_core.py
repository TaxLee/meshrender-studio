from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from meshrender_studio.core import expected_output_paths
from meshrender_studio.core import infer_source_kind
from meshrender_studio.core import normalize_batch_config


class CoreTests(unittest.TestCase):
    def test_infer_source_kind(self) -> None:
        self.assertEqual(infer_source_kind(Path("demo.inp")), "abaqus_inp")
        self.assertEqual(infer_source_kind(Path("demo.LIS")), "aqwa_lis")
        self.assertEqual(infer_source_kind(Path("mesh.vtu")), "vtu")
        self.assertEqual(infer_source_kind(Path("mesh.vtk")), "vtk")

    def test_normalize_batch_config_resolves_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            config = {
                "mesh_output_dir": "mesh",
                "figure_output_dir": "figures",
                "views": [
                    {
                        "name": "oblique",
                        "azimuth": 58,
                        "elevation": 28,
                        "roll": -8,
                        "zoom_factor": 1.0,
                    }
                ],
                "sources": [
                    {
                        "name": "sample",
                        "kind": "abaqus_inp",
                        "input": "inputs/demo.inp",
                        "figure_prefix": "demo",
                        "part_name": "",
                        "views": [],
                        "zoom_inset": {
                            "enabled": True,
                            "crop_box": [0.08, 0.5, 0.2, 0.24],
                            "inset_box": [0.35, 0.08, 0.3, 0.3],
                        },
                    }
                ],
            }
            normalized = normalize_batch_config(config, base_dir=base_dir)
            source = normalized["sources"][0]
            self.assertEqual(source["part_name"], None)
            self.assertTrue(source["zoom_inset"]["enabled"])
            self.assertEqual(source["zoom_inset"]["view"], "oblique")
            self.assertEqual(
                source["mesh_path"],
                (base_dir / "mesh" / "demo_abaqus_surface.vtu").resolve(),
            )
            self.assertEqual(source["figure_dir"], (base_dir / "figures").resolve())

            outputs = expected_output_paths(normalized)
            self.assertEqual(
                outputs["mesh"][0],
                (base_dir / "mesh" / "demo_abaqus_surface.vtu").resolve(),
            )
            self.assertEqual(
                outputs["figures"][0],
                (base_dir / "figures" / "demo.png").resolve(),
            )

    def test_normalize_batch_config_rejects_unknown_zoom_inset_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            config = {
                "mesh_output_dir": "mesh",
                "figure_output_dir": "figures",
                "views": [
                    {
                        "name": "oblique",
                        "azimuth": 58,
                        "elevation": 28,
                        "roll": -8,
                        "zoom_factor": 1.0,
                    }
                ],
                "sources": [
                    {
                        "name": "sample",
                        "kind": "vtu",
                        "input": "inputs/demo.vtu",
                        "figure_prefix": "demo",
                        "views": ["oblique"],
                        "zoom_inset": {
                            "enabled": True,
                            "view": "detail",
                        },
                    }
                ],
            }
            with self.assertRaisesRegex(ValueError, "zoom_inset view"):
                normalize_batch_config(config, base_dir=base_dir)


if __name__ == "__main__":
    unittest.main()
