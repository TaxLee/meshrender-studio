from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from meshrender_studio.core import normalize_batch_config
from meshrender_studio.job_queue import JobManager
from meshrender_studio.project_store import ProjectStore


class JobQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmpdir.name)
        self.store = ProjectStore(root_dir=self.repo_root, project_dir=self.repo_root)
        payload = self.store.make_template("Job Test")
        self.project_id = payload["project_id"]
        input_path = self.store.inputs_dir(self.project_id) / "sample.inp"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text("*Heading\n", encoding="utf-8")
        self.project = payload["project"]
        self.project["sources"] = [
            {
                "name": "sample",
                "kind": "abaqus_inp",
                "input": f"workspace/{self.project_id}/inputs/sample.inp",
                "figure_prefix": "sample",
                "views": ["oblique"],
                "part_name": "",
                "part_index": 0,
                "structure_filter": "",
            }
        ]

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_job_manager_runs_sequential_mocked_commands(self) -> None:
        manager = JobManager(self.store, project_dir=self.repo_root, autostart=True)
        project = self.project
        store = self.store

        def fake_run_command(job_id: str, command: list[str]) -> None:
            manager._append_log(job_id, f"mock {' '.join(command)}")
            normalized = normalize_batch_config(project, base_dir=self.repo_root)
            if any("cli_prepare.py" in part for part in command):
                for path in [item for item in [source["mesh_path"] for source in normalized["sources"]]]:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("mesh", encoding="utf-8")
            else:
                for path in normalize_batch_config(project, base_dir=self.repo_root)["sources"]:
                    figure = store.figures_dir(self.project_id) / f"{path['figure_prefix']}.png"
                    figure.parent.mkdir(parents=True, exist_ok=True)
                    figure.write_bytes(b"png")

        manager._run_command = fake_run_command  # type: ignore[method-assign]
        job = manager.enqueue_job(self.project_id, project, pvpython=sys.executable)
        result = manager.wait_for_job(job["job_id"], timeout=5.0)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["outputs"]["figures"])
        self.assertIn("mock", "\n".join(result["logs"]))


if __name__ == "__main__":
    unittest.main()
