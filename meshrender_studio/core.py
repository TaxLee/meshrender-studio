from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import copy
import json
import os
import re
import shutil


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
DEFAULT_CONFIG_PATH = PROJECT_DIR / "mesh_batch_config.json"
DEFAULT_PVPYTHON_CANDIDATES = [
    Path("/Applications/ParaView-6.1.0.app/Contents/bin/pvpython"),
]

VTK_TRIANGLE = 5
VTK_QUAD = 9
PROJECT_VERSION = 1

NUM_RE = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[EeDd][-+]?\d+)?"
AQWA_COORD_ROW_RE = re.compile(
    rf"^\s*(\d+)\s+(\d+)\s+(\d+)\s+({NUM_RE})\s+({NUM_RE})\s+({NUM_RE})\s*$"
)
AQWA_ELEM_ROW_RE = re.compile(r"^\s*(\d+)\s+([A-Za-z0-9]+)\b")
ABAQUS_TYPE_RE = re.compile(r"type\s*=\s*([^,\s]+)", re.IGNORECASE)
ABAQUS_PART_NAME_RE = re.compile(r"name\s*=\s*([^,\s]+)", re.IGNORECASE)

ABAQUS_TRI_TYPES = {
    "S3",
    "S3R",
    "STRI3",
    "M3D3",
    "R3D3",
    "CPS3",
    "CPE3",
    "CAX3",
}
ABAQUS_QUAD_TYPES = {
    "S4",
    "S4R",
    "S4R5",
    "S4RS",
    "M3D4",
    "R3D4",
    "CPS4",
    "CPS4R",
    "CPE4",
    "CPE4R",
    "CAX4",
    "CAX4R",
}
AQWA_QUAD_TYPES = {"QPPL", "MQPL"}
AQWA_TRI_TYPES = {"TPPL", "MTPL"}
DEFAULT_ZOOM_INSET_STROKE_COLOR = [0.95, 0.43, 0.16]
DEFAULT_ZOOM_INSET_CROP_BOX = [0.05, 0.54, 0.22, 0.26]
DEFAULT_ZOOM_INSET_INSET_BOX = [0.37, 0.08, 0.35, 0.35]


@dataclass
class MeshData:
    points: list[tuple[float, float, float]]
    triangles: list[tuple[int, int, int]] = field(default_factory=list)
    quads: list[tuple[int, int, int, int]] = field(default_factory=list)


def make_default_config() -> dict:
    return {
        "mesh_output_dir": "data/mesh/_pv_clean",
        "figure_output_dir": "data/mesh/_pv_clean/figures",
        "render_defaults": {
            "image_width": 2600,
            "image_height": 1800,
            "background": [1.0, 1.0, 1.0],
            "surface_color": [0.92, 0.92, 0.92],
            "edge_color": [0.15, 0.15, 0.15],
            "line_width": 1.0,
            "surface_opacity": 1.0,
            "parallel_projection": True,
        },
        "views": [
            {
                "name": "oblique",
                "azimuth": 58.0,
                "elevation": 28.0,
                "roll": -8.0,
                "zoom_factor": 1.0,
            }
        ],
        "sources": [
            {
                "name": "abaqus_mesh",
                "kind": "abaqus_inp",
                "input": "data/mesh/Job-6k.inp",
                "figure_prefix": "abaqus_clean",
            },
            {
                "name": "aqwa_mesh",
                "kind": "aqwa_lis",
                "input": "data/mesh/BemMesh4293.LIS",
                "figure_prefix": "aqwa_clean",
            },
        ],
    }


def make_default_zoom_inset(view_name: str | None = None) -> dict:
    return {
        "enabled": False,
        "view": view_name or "",
        "crop_box": copy.deepcopy(DEFAULT_ZOOM_INSET_CROP_BOX),
        "inset_box": copy.deepcopy(DEFAULT_ZOOM_INSET_INSET_BOX),
        "stroke_color": copy.deepcopy(DEFAULT_ZOOM_INSET_STROKE_COLOR),
        "stroke_width": 4.0,
    }


def make_project_template(project_id: str, project_name: str = "Untitled Project") -> dict:
    default_config = make_default_config()
    return {
        "version": PROJECT_VERSION,
        "project_name": project_name,
        "mesh_output_dir": f"workspace/{project_id}/mesh",
        "figure_output_dir": f"workspace/{project_id}/figures",
        "render_defaults": copy.deepcopy(default_config["render_defaults"]),
        "views": copy.deepcopy(default_config["views"]),
        "sources": [],
    }


def deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def resolve_relative_path(value: str | os.PathLike[str], base_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def repo_relative_path(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_DIR).as_posix()


def compact_upper(text: str) -> str:
    return re.sub(r"\s+", "", text.upper())


def to_float(token: str) -> float:
    return float(token.replace("D", "E").replace("d", "e"))


def format_float(value: float) -> str:
    return f"{value:.12g}"


def parse_csv_numbers(line: str) -> list[str]:
    return [item.strip() for item in line.split(",") if item.strip()]


def all_int_tokens(tokens: list[str]) -> bool:
    return all(re.fullmatch(r"[-+]?\d+", token) is not None for token in tokens)


def infer_source_kind(path: Path, explicit_kind: str | None = None) -> str:
    if explicit_kind and explicit_kind.lower() != "auto":
        return explicit_kind.lower()

    suffix = path.suffix.lower()
    if suffix == ".inp":
        return "abaqus_inp"
    if suffix == ".lis":
        return "aqwa_lis"
    if suffix == ".vtu":
        return "vtu"
    if suffix == ".vtk":
        return "vtk"
    raise ValueError(f"Cannot infer source kind from file extension: {path}")


def default_mesh_output_name(source: dict) -> str:
    input_path = source["input_path"]
    kind = source["kind"]
    if kind == "abaqus_inp":
        return f"{input_path.stem}_abaqus_surface.vtu"
    if kind == "aqwa_lis":
        return f"{input_path.stem}_aqwa_surface.vtu"
    return input_path.name


def build_figure_filename(source: dict, view_name: str) -> str:
    selected_views = source["views"]
    if source.get("figure_pattern"):
        return source["figure_pattern"].format(
            source=source["figure_prefix"],
            view=view_name,
            name=source["name"],
        )
    if source.get("figure_name") and len(selected_views) == 1:
        return source["figure_name"]

    needs_suffix = len(selected_views) > 1 or source.get("always_suffix_view_name", False)
    if needs_suffix:
        return f"{source['figure_prefix']}_{view_name}.png"
    return f"{source['figure_prefix']}.png"


def build_figure_path(source: dict, view_name: str) -> Path:
    return source["figure_dir"] / build_figure_filename(source, view_name)


def select_sources(config: dict, selected_names: list[str] | None = None) -> list[dict]:
    if not selected_names:
        return list(config["sources"])

    wanted = set(selected_names)
    matches = [
        source
        for source in config["sources"]
        if source["name"] in wanted
        or source["figure_prefix"] in wanted
        or source["input_path"].name in wanted
    ]
    if len(matches) != len(wanted):
        found = {
            source["name"]
            for source in matches
        } | {
            source["figure_prefix"]
            for source in matches
        } | {
            source["input_path"].name
            for source in matches
        }
        missing = sorted(wanted - found)
        raise ValueError(f"Unknown source selector(s): {', '.join(missing)}")
    return matches


def selected_views_for_source(
    config: dict,
    source: dict,
    selected_view_names: list[str] | None = None,
) -> list[dict]:
    names = selected_view_names or source["views"]
    unknown = [name for name in names if name not in config["view_lookup"]]
    if unknown:
        raise ValueError(
            f"Unknown view name(s) for source {source['name']}: {', '.join(sorted(unknown))}"
        )
    return [config["view_lookup"][name] for name in names]


def normalize_view(view: dict, index: int) -> dict:
    normalized = {
        "name": view.get("name", f"view_{index + 1}"),
        "azimuth": float(view.get("azimuth", 58.0)),
        "elevation": float(view.get("elevation", 28.0)),
        "roll": float(view.get("roll", -8.0)),
        "zoom_factor": float(view.get("zoom_factor", 1.0)),
    }
    if "parallel_projection" in view:
        normalized["parallel_projection"] = bool(view["parallel_projection"])
    return normalized


def normalize_unit_rect(value: object, label: str, source_name: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(
            f"Source {source_name} must define {label} as four normalized numbers "
            "(x, y, width, height)"
        )

    rect = [float(item) for item in value]
    x, y, width, height = rect
    if width <= 0 or height <= 0:
        raise ValueError(f"Source {source_name} must define positive width and height for {label}")
    if x < 0 or y < 0 or x + width > 1 or y + height > 1:
        raise ValueError(
            f"Source {source_name} must keep {label} inside the rendered image bounds"
        )
    return rect


def normalize_rgb_triplet(value: object, label: str, source_name: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(
            f"Source {source_name} must define {label} as three normalized RGB values"
        )
    color = [float(item) for item in value]
    if any(channel < 0 or channel > 1 for channel in color):
        raise ValueError(
            f"Source {source_name} must keep {label} values between 0 and 1"
        )
    return color


def normalize_zoom_inset(
    value: object,
    source_name: str,
    view_names: list[str],
) -> dict:
    default_view_name = view_names[0] if view_names else ""
    if value is None:
        return make_default_zoom_inset(default_view_name)
    if not isinstance(value, dict):
        raise ValueError(f"Source {source_name} must define zoom_inset as an object")

    merged = deep_merge(make_default_zoom_inset(default_view_name), value)
    target_view = merged.get("view") or default_view_name
    if target_view not in view_names:
        raise ValueError(
            f"Source {source_name} zoom_inset view must be one of: {', '.join(view_names)}"
        )

    stroke_width = float(merged.get("stroke_width", 4.0))
    if stroke_width <= 0:
        raise ValueError(f"Source {source_name} must define a positive zoom_inset stroke_width")

    return {
        "enabled": bool(merged.get("enabled", False)),
        "view": target_view,
        "crop_box": normalize_unit_rect(merged.get("crop_box"), "zoom_inset crop_box", source_name),
        "inset_box": normalize_unit_rect(
            merged.get("inset_box"),
            "zoom_inset inset_box",
            source_name,
        ),
        "stroke_color": normalize_rgb_triplet(
            merged.get("stroke_color"),
            "zoom_inset stroke_color",
            source_name,
        ),
        "stroke_width": stroke_width,
    }


def normalize_source(source: dict, config: dict, index: int, base_dir: Path) -> dict:
    if "input" not in source:
        raise ValueError(f"Source #{index + 1} is missing required key 'input'")

    input_path = resolve_relative_path(source["input"], base_dir)
    kind = infer_source_kind(input_path, source.get("kind"))
    name = source.get("name", input_path.stem)
    mesh_output_dir = config["mesh_output_dir"]
    figure_output_dir = config["figure_output_dir"]
    view_names = list(source.get("views") or config["view_order"])

    unknown = [view_name for view_name in view_names if view_name not in config["view_lookup"]]
    if unknown:
        raise ValueError(
            f"Source {name} references unknown view(s): {', '.join(sorted(unknown))}"
        )

    if kind in {"vtu", "vtk"}:
        mesh_path = input_path
    else:
        mesh_output = source.get("mesh_output") or source.get("vtu_output")
        if mesh_output:
            mesh_path = resolve_relative_path(mesh_output, base_dir)
        else:
            mesh_path = mesh_output_dir / default_mesh_output_name(
                {"kind": kind, "input_path": input_path}
            )

    figure_dir_value = source.get("figure_dir")
    figure_dir = (
        resolve_relative_path(figure_dir_value, base_dir)
        if figure_dir_value
        else figure_output_dir
    )

    normalized = {
        "name": name,
        "kind": kind,
        "input_path": input_path,
        "mesh_path": mesh_path,
        "figure_dir": figure_dir,
        "figure_prefix": source.get("figure_prefix") or name,
        "figure_name": source.get("figure_name"),
        "figure_pattern": source.get("figure_pattern"),
        "always_suffix_view_name": bool(source.get("always_suffix_view_name", False)),
        "views": view_names,
        "render": deep_merge(config["render_defaults"], source.get("render", {})),
        "part_name": source.get("part_name") or None,
        "part_index": int(source.get("part_index", 0)),
        "structure_filter": source.get("structure_filter") or None,
        "zoom_inset": normalize_zoom_inset(source.get("zoom_inset"), name, view_names),
    }
    return normalized


def normalize_batch_config(
    config: dict,
    base_dir: Path = PROJECT_DIR,
    *,
    allow_empty_sources: bool = False,
) -> dict:
    merged = deep_merge(make_default_config(), config)
    merged["mesh_output_dir"] = resolve_relative_path(merged["mesh_output_dir"], base_dir)
    merged["figure_output_dir"] = resolve_relative_path(merged["figure_output_dir"], base_dir)
    merged["render_defaults"] = deep_merge(
        make_default_config()["render_defaults"],
        merged.get("render_defaults", {}),
    )

    raw_views = merged.get("views") or make_default_config()["views"]
    normalized_views: list[dict] = []
    seen_views: set[str] = set()
    for index, raw_view in enumerate(raw_views):
        view = normalize_view(raw_view, index)
        if view["name"] in seen_views:
            raise ValueError(f"Duplicate view name in config: {view['name']}")
        seen_views.add(view["name"])
        normalized_views.append(view)

    merged["views"] = normalized_views
    merged["view_lookup"] = {view["name"]: view for view in normalized_views}
    merged["view_order"] = [view["name"] for view in normalized_views]
    merged["base_dir"] = base_dir

    raw_sources = merged.get("sources") or []
    if not raw_sources and not allow_empty_sources:
        raise ValueError("Config must define at least one source")
    merged["sources"] = [
        normalize_source(raw_source, merged, index, base_dir)
        for index, raw_source in enumerate(raw_sources)
    ]
    return merged


def load_batch_config(
    config_path: str | os.PathLike[str] | None = None,
    *,
    base_dir: Path = PROJECT_DIR,
    allow_empty_sources: bool = False,
) -> dict:
    resolved_config_path = None
    if config_path is not None:
        resolved_config_path = resolve_relative_path(config_path, base_dir)
    elif DEFAULT_CONFIG_PATH.exists():
        resolved_config_path = DEFAULT_CONFIG_PATH

    config = make_default_config()
    if resolved_config_path is not None:
        with resolved_config_path.open("r", encoding="utf-8") as handle:
            user_config = json.load(handle)
        config = deep_merge(config, user_config)

    normalized = normalize_batch_config(
        config,
        base_dir=base_dir,
        allow_empty_sources=allow_empty_sources,
    )
    normalized["config_path"] = resolved_config_path
    return normalized


def write_ascii_data_array(handle, values: list[object], indent: str) -> None:
    if values:
        handle.write(indent)
        handle.write(" ".join(str(value) for value in values))
        handle.write("\n")


def write_vtu(mesh: MeshData, out_path: Path) -> None:
    num_points = len(mesh.points)
    num_cells = len(mesh.triangles) + len(mesh.quads)
    if num_points == 0 or num_cells == 0:
        raise RuntimeError(f"Cannot write empty VTU mesh to {out_path}")

    connectivity: list[int] = []
    offsets: list[int] = []
    types: list[int] = []
    cursor = 0

    for cell in mesh.triangles:
        connectivity.extend(cell)
        cursor += len(cell)
        offsets.append(cursor)
        types.append(VTK_TRIANGLE)
    for cell in mesh.quads:
        connectivity.extend(cell)
        cursor += len(cell)
        offsets.append(cursor)
        types.append(VTK_QUAD)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        handle.write('<?xml version="1.0"?>\n')
        handle.write(
            '<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">\n'
        )
        handle.write("  <UnstructuredGrid>\n")
        handle.write(
            f'    <Piece NumberOfPoints="{num_points}" NumberOfCells="{num_cells}">\n'
        )
        handle.write("      <Points>\n")
        handle.write(
            '        <DataArray type="Float64" NumberOfComponents="3" format="ascii">\n'
        )
        for x, y, z in mesh.points:
            handle.write(
                f"          {format_float(x)} {format_float(y)} {format_float(z)}\n"
            )
        handle.write("        </DataArray>\n")
        handle.write("      </Points>\n")
        handle.write("      <Cells>\n")
        handle.write('        <DataArray type="Int64" Name="connectivity" format="ascii">\n')
        write_ascii_data_array(handle, connectivity, "          ")
        handle.write("        </DataArray>\n")
        handle.write('        <DataArray type="Int64" Name="offsets" format="ascii">\n')
        write_ascii_data_array(handle, offsets, "          ")
        handle.write("        </DataArray>\n")
        handle.write('        <DataArray type="UInt8" Name="types" format="ascii">\n')
        write_ascii_data_array(handle, types, "          ")
        handle.write("        </DataArray>\n")
        handle.write("      </Cells>\n")
        handle.write("    </Piece>\n")
        handle.write("  </UnstructuredGrid>\n")
        handle.write("</VTKFile>\n")


def build_mesh_from_node_map(
    node_map: dict[object, tuple[float, float, float]],
    triangles_in: list[tuple[object, object, object]],
    quads_in: list[tuple[object, object, object, object]],
) -> MeshData:
    if not triangles_in and not quads_in:
        raise RuntimeError("No surface elements were parsed.")

    used_keys: list[object] = []
    seen: set[object] = set()
    for cell in triangles_in:
        for key in cell:
            if key not in seen:
                seen.add(key)
                used_keys.append(key)
    for cell in quads_in:
        for key in cell:
            if key not in seen:
                seen.add(key)
                used_keys.append(key)

    missing = [key for key in used_keys if key not in node_map]
    if missing:
        preview = ", ".join(str(key) for key in missing[:8])
        raise RuntimeError(f"Parsed elements reference missing nodes: {preview}")

    index_map = {key: idx for idx, key in enumerate(used_keys)}
    points = [node_map[key] for key in used_keys]
    triangles = [tuple(index_map[key] for key in cell) for cell in triangles_in]
    quads = [tuple(index_map[key] for key in cell) for cell in quads_in]
    return MeshData(points=points, triangles=triangles, quads=quads)


def abaqus_cell_family(element_type: str, node_count: int) -> str | None:
    etype = element_type.upper()
    if etype in ABAQUS_TRI_TYPES or node_count == 3:
        return "triangle"
    if etype in ABAQUS_QUAD_TYPES or node_count == 4:
        return "quad"
    return None


def parse_abaqus_inp(
    inp_path: Path,
    part_name: str | None = None,
    part_index: int = 0,
) -> MeshData:
    nodes: dict[int, tuple[float, float, float]] = {}
    triangles_raw: list[tuple[int, int, int]] = []
    quads_raw: list[tuple[int, int, int, int]] = []

    mode: str | None = None
    current_element_type = ""
    capture_part = False
    seen_parts = -1
    matched_part_name = None
    target_reached = False

    with inp_path.open("r", encoding="latin-1", errors="ignore") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped or stripped.startswith("**"):
                continue

            if stripped.startswith("*"):
                upper = stripped.upper()
                if upper.startswith("*PART"):
                    seen_parts += 1
                    match = ABAQUS_PART_NAME_RE.search(stripped)
                    current_part_name = match.group(1) if match else None
                    capture_part = False
                    mode = None

                    if part_name is not None:
                        capture_part = current_part_name == part_name
                        if capture_part:
                            matched_part_name = current_part_name
                    else:
                        capture_part = seen_parts == part_index
                    continue

                if upper.startswith("*END PART"):
                    if capture_part:
                        target_reached = True
                        break
                    capture_part = False
                    mode = None
                    continue

                if not capture_part:
                    continue

                if upper.startswith("*NODE"):
                    mode = "node"
                    continue
                if upper.startswith("*ELEMENT"):
                    match = ABAQUS_TYPE_RE.search(stripped)
                    current_element_type = match.group(1).upper() if match else ""
                    mode = "element"
                    continue
                mode = None
                continue

            if not capture_part:
                continue

            if mode == "node":
                items = parse_csv_numbers(raw)
                if len(items) < 4:
                    continue
                node_id = int(float(items[0]))
                nodes[node_id] = (
                    to_float(items[1]),
                    to_float(items[2]),
                    to_float(items[3]),
                )
                continue

            if mode == "element":
                items = parse_csv_numbers(raw)
                if len(items) < 4:
                    continue
                conn = tuple(int(float(token)) for token in items[1:])
                family = abaqus_cell_family(current_element_type, len(conn))
                if family == "triangle" and len(conn) >= 3:
                    triangles_raw.append(conn[:3])
                elif family == "quad" and len(conn) >= 4:
                    quads_raw.append(conn[:4])

    if part_name is not None and matched_part_name is None:
        raise RuntimeError(f"Part {part_name!r} was not found in {inp_path}")
    if part_name is None and not target_reached and seen_parts < part_index:
        raise RuntimeError(f"Part index {part_index} was not found in {inp_path}")
    if not nodes:
        raise RuntimeError(f"No Abaqus nodes were parsed from target part in {inp_path}")

    mesh = build_mesh_from_node_map(nodes, triangles_raw, quads_raw)
    print(
        f"[ok] Parsed Abaqus mesh: {len(mesh.points)} points, "
        f"{len(mesh.quads)} quads, {len(mesh.triangles)} triangles"
    )
    return mesh


def parse_aqwa_lis(lis_path: Path, structure_filter: int | None = None) -> MeshData:
    nodes: dict[tuple[int, int], tuple[float, float, float]] = {}
    triangles_raw: list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]] = []
    quads_raw: list[
        tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]
    ] = []

    mode: str | None = None
    current_structure: int | None = None

    with lis_path.open("r", encoding="latin-1", errors="ignore") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue

            compact = compact_upper(raw)
            if "COORDINATEDATA" in compact:
                mode = "coord"
                continue

            match = re.search(r"ELEMENTTOPOLOGYFORSTRUCTURE(\d+)", compact)
            if match:
                current_structure = int(match.group(1))
                mode = "element"
                continue

            if stripped.isdigit():
                continue

            if mode == "coord":
                coord_match = AQWA_COORD_ROW_RE.match(raw)
                if not coord_match:
                    continue
                structure_id = int(coord_match.group(2))
                if structure_filter is not None and structure_id != structure_filter:
                    continue
                node_id = int(coord_match.group(3))
                nodes[(structure_id, node_id)] = (
                    to_float(coord_match.group(4)),
                    to_float(coord_match.group(5)),
                    to_float(coord_match.group(6)),
                )
                continue

            if mode == "element":
                elem_match = AQWA_ELEM_ROW_RE.match(raw)
                if not elem_match or current_structure is None:
                    continue
                if structure_filter is not None and current_structure != structure_filter:
                    continue

                items = stripped.split()
                if len(items) < 8:
                    continue
                etype = items[1].upper()
                structure = current_structure

                if (
                    etype in AQWA_QUAD_TYPES
                    and len(items) >= 9
                    and all_int_tokens(items[2:9])
                ):
                    conn = tuple((structure, int(items[idx])) for idx in range(2, 6))
                    quads_raw.append(conn)
                elif (
                    etype in AQWA_TRI_TYPES
                    and len(items) >= 8
                    and all_int_tokens(items[2:8])
                ):
                    conn = tuple((structure, int(items[idx])) for idx in range(2, 5))
                    triangles_raw.append(conn)

    if not nodes:
        raise RuntimeError(
            "No AQWA nodes were parsed from the printed coordinate tables. "
            "Inspect the .LIS layout if you are using a different AQWA version."
        )

    mesh = build_mesh_from_node_map(nodes, triangles_raw, quads_raw)
    print(
        f"[ok] Parsed AQWA mesh: {len(mesh.points)} points, "
        f"{len(mesh.quads)} quads, {len(mesh.triangles)} triangles"
    )
    return mesh


def prepare_source(source: dict) -> Path:
    kind = source["kind"]
    input_path = source["input_path"]
    mesh_path = source["mesh_path"]

    if kind == "abaqus_inp":
        mesh = parse_abaqus_inp(
            input_path,
            part_name=source.get("part_name"),
            part_index=source.get("part_index", 0),
        )
        write_vtu(mesh, mesh_path)
        print(f"[ok] Abaqus -> {mesh_path}")
        return mesh_path

    if kind == "aqwa_lis":
        structure_filter = source.get("structure_filter")
        if structure_filter is not None:
            structure_filter = int(structure_filter)
        mesh = parse_aqwa_lis(input_path, structure_filter=structure_filter)
        write_vtu(mesh, mesh_path)
        print(f"[ok] AQWA -> {mesh_path}")
        return mesh_path

    if kind in {"vtu", "vtk"}:
        print(f"[ok] Using existing mesh -> {mesh_path}")
        return mesh_path

    raise ValueError(f"Unsupported source kind: {kind}")


def prepare_sources(config: dict, selected_names: list[str] | None = None) -> list[Path]:
    config["mesh_output_dir"].mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for source in select_sources(config, selected_names):
        outputs.append(prepare_source(source))
    return outputs


def expected_output_paths(
    config: dict,
    selected_sources: list[str] | None = None,
    selected_views: list[str] | None = None,
) -> dict[str, list[Path]]:
    mesh_paths: list[Path] = []
    figure_paths: list[Path] = []
    for source in select_sources(config, selected_sources):
        mesh_paths.append(source["mesh_path"])
        for view in selected_views_for_source(config, source, selected_views):
            figure_paths.append(build_figure_path(source, view["name"]))
    return {"mesh": mesh_paths, "figures": figure_paths}


def find_pvpython(explicit_path: str | None = None) -> str:
    candidates: list[str] = []
    if explicit_path:
        candidates.append(explicit_path)

    env_value = os.environ.get("PVPYTHON")
    if env_value:
        candidates.append(env_value)

    which_path = shutil.which("pvpython")
    if which_path:
        candidates.append(which_path)

    for path in DEFAULT_PVPYTHON_CANDIDATES:
        candidates.append(str(path))

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_absolute():
            if path.exists():
                return str(path)
        else:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved

    raise FileNotFoundError(
        "Could not locate pvpython. Set the PVPYTHON environment variable or pass --pvpython."
    )
