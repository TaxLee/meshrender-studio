from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pathlib import Path

from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from flask import send_from_directory

from meshrender_studio.core import PROJECT_DIR
from meshrender_studio.core import find_pvpython
from meshrender_studio.job_queue import JobManager
from meshrender_studio.project_store import ProjectStore


def create_app(
    *,
    testing: bool = False,
    root_dir: Path | None = None,
    project_dir: Path = PROJECT_DIR,
    autostart_jobs: bool = True,
) -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["TESTING"] = testing
    app.config["PROJECT_STORE"] = ProjectStore(root_dir=root_dir, project_dir=project_dir)
    app.config["JOB_MANAGER"] = JobManager(
        app.config["PROJECT_STORE"],
        project_dir=project_dir,
        autostart=autostart_jobs,
    )

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/projects")
    def list_projects():
        store: ProjectStore = app.config["PROJECT_STORE"]
        return jsonify({"projects": store.list_projects()})

    @app.get("/api/project/template")
    def project_template():
        store: ProjectStore = app.config["PROJECT_STORE"]
        project_name = request.args.get("project_name", "Untitled Project")
        return jsonify(store.make_template(project_name))

    @app.post("/api/project/import-files")
    def import_files():
        store: ProjectStore = app.config["PROJECT_STORE"]
        project_id = request.form.get("project_id")
        if not project_id:
            return jsonify({"error": "project_id is required"}), 400
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "At least one file upload is required"}), 400
        return jsonify(store.import_files(project_id, files))

    @app.post("/api/project/save")
    def save_project():
        store: ProjectStore = app.config["PROJECT_STORE"]
        payload = request.get_json(silent=True) or {}
        project_id = payload.get("project_id")
        project = payload.get("project")
        if not project_id or not isinstance(project, dict):
            return jsonify({"error": "project_id and project are required"}), 400
        try:
            result = store.save_project(project_id, project)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.post("/api/project/load")
    def load_project():
        store: ProjectStore = app.config["PROJECT_STORE"]
        payload = request.get_json(silent=True) or {}
        project_id = payload.get("project_id")
        if not project_id:
            return jsonify({"error": "project_id is required"}), 400
        try:
            result = store.load_project(project_id)
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify(result)

    @app.get("/api/system")
    def system_status():
        try:
            pvpython = find_pvpython()
            return jsonify({"pvpython": pvpython, "available": True})
        except Exception as exc:
            return jsonify({"pvpython": None, "available": False, "error": str(exc)})

    @app.post("/api/jobs")
    def create_job():
        manager: JobManager = app.config["JOB_MANAGER"]
        payload = request.get_json(silent=True) or {}
        project_id = payload.get("project_id")
        project = payload.get("project")
        pvpython = payload.get("pvpython")
        if not project_id or not isinstance(project, dict):
            return jsonify({"error": "project_id and project are required"}), 400
        try:
            job = manager.enqueue_job(project_id, project, pvpython=pvpython)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(job), 202

    @app.get("/api/jobs/<job_id>")
    def get_job(job_id: str):
        manager: JobManager = app.config["JOB_MANAGER"]
        try:
            job = manager.get_job(job_id)
        except KeyError:
            return jsonify({"error": f"Job {job_id} was not found"}), 404
        return jsonify(job)

    @app.get("/api/files/<project_id>/<kind>/<path:name>")
    def get_artifact(project_id: str, kind: str, name: str):
        store: ProjectStore = app.config["PROJECT_STORE"]
        if kind == "mesh":
            directory = store.mesh_dir(project_id)
        elif kind == "figures":
            directory = store.figures_dir(project_id)
        elif kind == "inputs":
            directory = store.inputs_dir(project_id)
        else:
            return jsonify({"error": f"Unsupported artifact kind: {kind}"}), 404
        return send_from_directory(directory, name, as_attachment=False)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
