from __future__ import annotations

from pathlib import Path

from meshrender_studio.core import build_figure_path
from meshrender_studio.core import selected_views_for_source
from meshrender_studio.core import select_sources
from meshrender_studio.figure_layout import compose_zoom_inset
from paraview.simple import *


def make_reader(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".vtu":
        return XMLUnstructuredGridReader(FileName=[str(path)])
    if suffix == ".vtk":
        return LegacyVTKReader(FileNames=[str(path)])
    raise ValueError(f"Unsupported render input: {path}")


def apply_render_style(display, view, render_options: dict) -> None:
    display.Representation = "Surface With Edges"
    display.DiffuseColor = render_options["surface_color"]
    display.AmbientColor = render_options["surface_color"]
    display.EdgeColor = render_options["edge_color"]
    display.LineWidth = float(render_options["line_width"])
    display.Opacity = float(render_options["surface_opacity"])
    try:
        display.ColorArrayName = [None, ""]
    except Exception:
        pass

    try:
        LoadPalette(paletteName="WhiteBackground")
    except Exception:
        pass
    try:
        view.UseColorPaletteForBackground = 0
    except Exception:
        pass

    background = render_options["background"]
    view.Background = background
    try:
        view.Background2 = background
    except Exception:
        pass
    try:
        view.UseGradientBackground = 0
    except Exception:
        pass
    view.OrientationAxesVisibility = 0
    view.CenterAxesVisibility = 0
    view.ViewSize = [
        int(render_options["image_width"]),
        int(render_options["image_height"]),
    ]
    view.InteractionMode = "3D"


def standardize_camera(view, render_options: dict, view_options: dict) -> None:
    ResetCamera(view)
    camera = GetActiveCamera()
    camera.Azimuth(float(view_options["azimuth"]))
    camera.Elevation(float(view_options["elevation"]))
    camera.Roll(float(view_options["roll"]))
    camera.OrthogonalizeViewUp()
    ResetCamera(view)

    parallel_projection = bool(
        view_options.get(
            "parallel_projection",
            render_options.get("parallel_projection", True),
        )
    )
    view.CameraParallelProjection = 1 if parallel_projection else 0

    zoom_factor = float(view_options.get("zoom_factor", 1.0))
    if zoom_factor != 1.0:
        camera.Zoom(zoom_factor)


def render_one(
    mesh_path: Path,
    output_png: Path,
    render_options: dict,
    view_options: dict,
    zoom_inset: dict | None = None,
) -> None:
    if not mesh_path.exists():
        raise FileNotFoundError(
            f"Mesh file not found for rendering: {mesh_path}. "
            "Run python3 -m meshrender_studio.cli_prepare first, or use cli_run."
        )

    reader = make_reader(mesh_path)
    view = CreateView("RenderView")
    SetActiveView(view)
    SetActiveSource(reader)

    display = Show(reader, view)
    apply_render_style(display, view, render_options)
    Render(view)
    standardize_camera(view, render_options, view_options)
    Render(view)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    SaveScreenshot(
        str(output_png),
        view,
        ImageResolution=[
            int(render_options["image_width"]),
            int(render_options["image_height"]),
        ],
    )
    if zoom_inset and zoom_inset.get("enabled"):
        compose_zoom_inset(output_png, zoom_inset)
    print(f"[ok] Wrote {output_png}")

    Delete(display)
    Delete(view)
    Delete(reader)


def render_config(
    config: dict,
    selected_sources: list[str] | None = None,
    selected_views: list[str] | None = None,
) -> list[Path]:
    outputs: list[Path] = []
    for source in select_sources(config, selected_sources):
        mesh_path = source["mesh_path"]
        render_options = source["render"]
        zoom_inset = source.get("zoom_inset")
        for view_options in selected_views_for_source(config, source, selected_views):
            output_png = build_figure_path(source, view_options["name"])
            active_zoom_inset = None
            if zoom_inset and zoom_inset.get("view") == view_options["name"]:
                active_zoom_inset = zoom_inset
            render_one(mesh_path, output_png, render_options, view_options, active_zoom_inset)
            outputs.append(output_png)
    return outputs
