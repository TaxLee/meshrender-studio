from __future__ import annotations

from pathlib import Path
import copy
import json
import re
import secrets

from meshrender_studio.core import PROJECT_DIR
from meshrender_studio.core import PROJECT_VERSION
from meshrender_studio.core import infer_source_kind
from meshrender_studio.core import make_default_config
from meshrender_studio.core import normalize_batch_config


def slugify(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-.")
    return text or "project"


def safe_filename(name: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return text or "file"


class ProjectStore:
    def __init__(
        self,
        root_dir: Path | None = None,
        *,
        project_dir: Path = PROJECT_DIR,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.root_dir = Path(root_dir or self.project_dir).resolve()
        self.projects_dir = self.root_dir / "projects"
        self.workspace_dir = self.root_dir / "workspace"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def to_repo_relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.project_dir).as_posix()

    def _workspace_root(self, project_id: str) -> Path:
        return self.workspace_dir / project_id

    def inputs_dir(self, project_id: str) -> Path:
        return self._workspace_root(project_id) / "inputs"

    def mesh_dir(self, project_id: str) -> Path:
        return self._workspace_root(project_id) / "mesh"

    def figures_dir(self, project_id: str) -> Path:
        return self._workspace_root(project_id) / "figures"

    def runtime_config_path(self, project_id: str) -> Path:
        return self._workspace_root(project_id) / "current_project.json"

    def project_file_path(self, project_id: str) -> Path:
        return self.projects_dir / f"{project_id}.json"

    def ensure_workspace(self, project_id: str) -> None:
        self.inputs_dir(project_id).mkdir(parents=True, exist_ok=True)
        self.mesh_dir(project_id).mkdir(parents=True, exist_ok=True)
        self.figures_dir(project_id).mkdir(parents=True, exist_ok=True)

    def generate_project_id(self, project_name: str = "Untitled Project") -> str:
        return f"{slugify(project_name)}-{secrets.token_hex(4)}"

    def make_template(self, project_name: str = "Untitled Project") -> dict:
        project_id = self.generate_project_id(project_name)
        self.ensure_workspace(project_id)
        default_config = make_default_config()
        project = {
            "version": PROJECT_VERSION,
            "project_name": project_name,
            "mesh_output_dir": self.to_repo_relative(self.mesh_dir(project_id)),
            "figure_output_dir": self.to_repo_relative(self.figures_dir(project_id)),
            "render_defaults": copy.deepcopy(default_config["render_defaults"]),
            "views": copy.deepcopy(default_config["views"]),
            "sources": [],
        }
        return {"project_id": project_id, "project": project}

    def _normalize_project_paths(self, project_id: str, project: dict) -> dict:
        payload = copy.deepcopy(project)
        payload["version"] = PROJECT_VERSION
        payload["project_name"] = payload.get("project_name") or "Untitled Project"
        payload["mesh_output_dir"] = self.to_repo_relative(self.mesh_dir(project_id))
        payload["figure_output_dir"] = self.to_repo_relative(self.figures_dir(project_id))
        payload.setdefault("render_defaults", copy.deepcopy(make_default_config()["render_defaults"]))
        payload.setdefault("views", copy.deepcopy(make_default_config()["views"]))
        payload.setdefault("sources", [])

        for source in payload["sources"]:
            for key in ("input", "mesh_output", "figure_dir"):
                value = source.get(key)
                if not value:
                    continue
                path = Path(value)
                if path.is_absolute() and self.project_dir in path.resolve().parents:
                    source[key] = self.to_repo_relative(path)
        return payload

    def validate_project(self, project_id: str, project: dict, *, allow_empty_sources: bool) -> dict:
        prepared = self._normalize_project_paths(project_id, project)
        normalize_batch_config(
            prepared,
            base_dir=self.project_dir,
            allow_empty_sources=allow_empty_sources,
        )
        return prepared

    def save_project(self, project_id: str, project: dict) -> dict:
        self.ensure_workspace(project_id)
        prepared = self.validate_project(project_id, project, allow_empty_sources=True)
        project_path = self.project_file_path(project_id)
        project_path.write_text(json.dumps(prepared, indent=2), encoding="utf-8")
        return {
            "project_id": project_id,
            "project_path": self.to_repo_relative(project_path),
            "project": prepared,
        }

    def write_runtime_config(self, project_id: str, project: dict) -> Path:
        self.ensure_workspace(project_id)
        prepared = self.validate_project(project_id, project, allow_empty_sources=False)
        config_path = self.runtime_config_path(project_id)
        config_path.write_text(json.dumps(prepared, indent=2), encoding="utf-8")
        return config_path

    def load_project(self, project_id: str) -> dict:
        project_path = self.project_file_path(project_id)
        if not project_path.exists():
            raise FileNotFoundError(f"Project {project_id} was not found")
        project = json.loads(project_path.read_text(encoding="utf-8"))
        self.ensure_workspace(project_id)
        return {
            "project_id": project_id,
            "project_path": self.to_repo_relative(project_path),
            "project": project,
        }

    def list_projects(self) -> list[dict]:
        items: list[dict] = []
        for path in sorted(
            self.projects_dir.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            items.append(
                {
                    "project_id": path.stem,
                    "project_name": payload.get("project_name", path.stem),
                    "project_path": self.to_repo_relative(path),
                    "updated_at": path.stat().st_mtime,
                }
            )
        return items

    def _unique_input_path(self, project_id: str, filename: str) -> Path:
        target = self.inputs_dir(project_id)
        target.mkdir(parents=True, exist_ok=True)
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        candidate = target / filename
        counter = 1
        while candidate.exists():
            candidate = target / f"{stem}_{counter}{suffix}"
            counter += 1
        return candidate

    def import_files(self, project_id: str, uploaded_files: list[object]) -> dict:
        self.ensure_workspace(project_id)
        imported: list[dict] = []

        for storage in uploaded_files:
            original_name = getattr(storage, "filename", "") or "uploaded-file"
            filename = safe_filename(Path(original_name).name)
            destination = self._unique_input_path(project_id, filename)
            storage.save(destination)

            try:
                kind = infer_source_kind(destination)
            except ValueError:
                kind = "auto"

            source = {
                "name": destination.stem,
                "kind": kind,
                "input": self.to_repo_relative(destination),
                "figure_prefix": destination.stem,
                "views": ["oblique"],
                "part_name": "",
                "part_index": 0,
                "structure_filter": "",
            }
            imported.append(
                {
                    "name": destination.name,
                    "input": source["input"],
                    "kind": kind,
                    "source": source,
                }
            )

        return {"project_id": project_id, "files": imported}
