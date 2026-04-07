from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest

from meshrender_studio.app import create_app
from meshrender_studio.core import normalize_batch_config


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmpdir.name)
        self.app = create_app(
            testing=True,
            root_dir=self.repo_root,
            project_dir=self.repo_root,
            autostart_jobs=True,
        )
        self.client = self.app.test_client()
        self.store = self.app.config["PROJECT_STORE"]
        self.manager = self.app.config["JOB_MANAGER"]

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_flask_workflow_end_to_end(self) -> None:
        index_response = self.client.get("/")
        self.assertEqual(index_response.status_code, 200)
        self.assertIn(b"MeshRender Studio", index_response.data)
        self.assertIn(b"Shuijin Li", index_response.data)

        template = self.client.get("/api/project/template").get_json()
        project_id = template["project_id"]
        project = template["project"]
        project["views"][0]["azimuth"] = 45
        project["views"][0]["elevation"] = 30
        project["views"][0]["roll"] = -10

        import_response = self.client.post(
            "/api/project/import-files",
            data={
                "project_id": project_id,
                "files": (BytesIO(b"*Heading\n"), "demo.inp"),
            },
            content_type="multipart/form-data",
        ).get_json()
        source = import_response["files"][0]["source"]
        project["sources"] = [source]

        save_response = self.client.post(
            "/api/project/save",
            json={"project_id": project_id, "project": project},
        )
        self.assertEqual(save_response.status_code, 200)

        load_response = self.client.post(
            "/api/project/load",
            json={"project_id": project_id},
        )
        self.assertEqual(load_response.status_code, 200)
        loaded_project = load_response.get_json()["project"]
        self.assertIsInstance(loaded_project["views"][0]["azimuth"], (int, float))
        self.assertIsInstance(loaded_project["views"][0]["elevation"], (int, float))
        self.assertIsInstance(loaded_project["views"][0]["roll"], (int, float))
        self.assertEqual(loaded_project["views"][0]["azimuth"], 45)

        def fake_run_command(job_id: str, command: list[str]) -> None:
            self.manager._append_log(job_id, f"mock {' '.join(command)}")
            normalized = normalize_batch_config(project, base_dir=self.repo_root)
            if any("cli_prepare.py" in part for part in command):
                for mesh_path in [item["mesh_path"] for item in normalized["sources"]]:
                    mesh_path.parent.mkdir(parents=True, exist_ok=True)
                    mesh_path.write_text("mesh", encoding="utf-8")
            else:
                figure = self.store.figures_dir(project_id) / "demo.png"
                figure.parent.mkdir(parents=True, exist_ok=True)
                figure.write_bytes(b"png")

        self.manager._run_command = fake_run_command  # type: ignore[method-assign]

        job_response = self.client.post(
            "/api/jobs",
            json={"project_id": project_id, "project": project, "pvpython": sys.executable},
        )
        self.assertEqual(job_response.status_code, 202)
        job_id = job_response.get_json()["job_id"]
        finished = self.manager.wait_for_job(job_id, timeout=5.0)
        self.assertEqual(finished["status"], "completed")

        status_response = self.client.get(f"/api/jobs/{job_id}")
        self.assertEqual(status_response.status_code, 200)
        status_payload = status_response.get_json()
        self.assertEqual(status_payload["status"], "completed")
        self.assertTrue(status_payload["outputs"]["figures"])

        figure_response = self.client.get(f"/api/files/{project_id}/figures/demo.png")
        self.assertEqual(figure_response.status_code, 200)
        self.assertEqual(figure_response.data, b"png")
        figure_response.close()


if __name__ == "__main__":
    unittest.main()
