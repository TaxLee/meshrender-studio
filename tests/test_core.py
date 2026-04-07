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
                    }
                ],
            }
            normalized = normalize_batch_config(config, base_dir=base_dir)
            source = normalized["sources"][0]
            self.assertEqual(source["part_name"], None)
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


if __name__ == "__main__":
    unittest.main()
