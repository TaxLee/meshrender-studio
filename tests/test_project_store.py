from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from meshrender_studio.project_store import ProjectStore


class FakeStorage:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content

    def save(self, destination: str | Path) -> None:
        Path(destination).write_bytes(self._content)


class ProjectStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmpdir.name)
        self.store = ProjectStore(root_dir=self.repo_root, project_dir=self.repo_root)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_save_and_load_project_round_trip(self) -> None:
        payload = self.store.make_template("Round Trip")
        result = self.store.save_project(payload["project_id"], payload["project"])
        loaded = self.store.load_project(payload["project_id"])
        self.assertEqual(result["project"]["project_name"], "Round Trip")
        self.assertEqual(loaded["project"]["project_name"], "Round Trip")
        self.assertTrue(self.store.project_file_path(payload["project_id"]).exists())

    def test_import_files_creates_workspace_source(self) -> None:
        payload = self.store.make_template("Import Test")
        imported = self.store.import_files(
            payload["project_id"],
            [FakeStorage("Example.inp", b"*Heading\n")],
        )
        self.assertEqual(imported["files"][0]["kind"], "abaqus_inp")
        self.assertTrue((self.store.inputs_dir(payload["project_id"]) / "Example.inp").exists())
        self.assertEqual(
            imported["files"][0]["source"]["input"],
            f"workspace/{payload['project_id']}/inputs/Example.inp",
        )


if __name__ == "__main__":
    unittest.main()
