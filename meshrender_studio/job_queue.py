from __future__ import annotations

from pathlib import Path
import copy
import queue
import subprocess
import sys
import threading
import time
import uuid

from meshrender_studio.core import expected_output_paths
from meshrender_studio.core import find_pvpython
from meshrender_studio.core import normalize_batch_config
from meshrender_studio.project_store import ProjectStore


PACKAGE_DIR = Path(__file__).resolve().parent


class JobManager:
    def __init__(
        self,
        project_store: ProjectStore,
        *,
        project_dir: Path,
        autostart: bool = True,
    ) -> None:
        self.project_store = project_store
        self.project_dir = Path(project_dir).resolve()
        self.jobs: dict[str, dict] = {}
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        if autostart:
            self.start()

    def start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def enqueue_job(
        self,
        project_id: str,
        project: dict,
        *,
        pvpython: str | None = None,
    ) -> dict:
        config_path = self.project_store.write_runtime_config(project_id, project)
        normalized = normalize_batch_config(project, base_dir=self.project_dir)
        job_id = uuid.uuid4().hex
        job = {
            "job_id": job_id,
            "project_id": project_id,
            "status": "queued",
            "logs": [],
            "error": None,
            "created_at": time.time(),
            "started_at": None,
            "finished_at": None,
            "project": copy.deepcopy(project),
            "config_path": str(config_path),
            "outputs": {"figures": [], "mesh": []},
            "pvpython": None,
            "pvpython_override": pvpython,
            "source_count": len(normalized["sources"]),
        }
        with self._lock:
            self.jobs[job_id] = job
        self._queue.put(job_id)
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict:
        with self._lock:
            if job_id not in self.jobs:
                raise KeyError(job_id)
            return copy.deepcopy(self.jobs[job_id])

    def wait_for_job(self, job_id: str, timeout: float = 10.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.get_job(job_id)
            if job["status"] in {"completed", "failed"}:
                return job
            time.sleep(0.05)
        raise TimeoutError(f"Timed out waiting for job {job_id}")

    def _set_job_fields(self, job_id: str, **fields) -> None:
        with self._lock:
            self.jobs[job_id].update(fields)

    def _append_log(self, job_id: str, line: str) -> None:
        text = line.rstrip("\n")
        with self._lock:
            self.jobs[job_id]["logs"].append(text)

    def _worker_loop(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                self._run_job(job_id)
            finally:
                self._queue.task_done()

    def _run_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        self._set_job_fields(job_id, status="running", started_at=time.time())
        try:
            pvpython = find_pvpython(job["pvpython_override"])
            self._set_job_fields(job_id, pvpython=pvpython)

            prepare_cmd = [
                sys.executable,
                str(PACKAGE_DIR / "cli_prepare.py"),
                "--config",
                job["config_path"],
            ]
            render_cmd = [
                pvpython,
                str(PACKAGE_DIR / "cli_render.py"),
                "--config",
                job["config_path"],
            ]

            self._run_command(job_id, prepare_cmd)
            self._run_command(job_id, render_cmd)

            normalized = normalize_batch_config(job["project"], base_dir=self.project_dir)
            outputs = self._collect_outputs(job["project_id"], normalized)
            self._set_job_fields(
                job_id,
                status="completed",
                finished_at=time.time(),
                outputs=outputs,
            )
        except Exception as exc:
            self._append_log(job_id, f"[error] {exc}")
            self._set_job_fields(
                job_id,
                status="failed",
                finished_at=time.time(),
                error=str(exc),
            )

    def _run_command(self, job_id: str, command: list[str]) -> None:
        self._append_log(job_id, f"$ {' '.join(command)}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            self._append_log(job_id, line)
        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, command)

    def _collect_outputs(self, project_id: str, config: dict) -> dict:
        paths = expected_output_paths(config)
        mesh_items = []
        figure_items = []
        for path in paths["mesh"]:
            if path.exists():
                mesh_items.append(
                    {
                        "name": path.name,
                        "relative_path": self.project_store.to_repo_relative(path),
                        "url": f"/api/files/{project_id}/mesh/{path.name}",
                    }
                )
        for path in paths["figures"]:
            if path.exists():
                figure_items.append(
                    {
                        "name": path.name,
                        "relative_path": self.project_store.to_repo_relative(path),
                        "url": f"/api/files/{project_id}/figures/{path.name}",
                    }
                )
        return {"mesh": mesh_items, "figures": figure_items}
