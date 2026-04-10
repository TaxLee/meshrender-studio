# MeshRender Studio User Guide

## Overview

MeshRender Studio is a local browser-based workflow for importing engineering mesh files, generating ParaView-friendly surfaces, defining reusable camera views, and rendering figure batches for reporting or review.

## Prerequisites

- Python 3.9 or newer
- ParaView with `pvpython`
- Local filesystem access to your mesh input files

MeshRender Studio checks `PVPYTHON`, then `PATH`, then `/Applications/ParaView-6.1.0.app/Contents/bin/pvpython`.

## Installation

1. Open a terminal in the project directory.
2. Install the package in editable mode:

```bash
python3 -m pip install -e .
```

## Launching the App

Run:

```bash
python3 -m meshrender_studio.app
```

Then open `http://127.0.0.1:5000` in your browser.

## Supported Input Types

- Abaqus input decks: `.inp`
- AQWA listings: `.LIS`
- ParaView-ready meshes: `.vtu`
- Legacy VTK meshes: `.vtk`

Imported files are copied into the active project's `workspace/<project-id>/inputs/` directory so the project remains self-contained.

## Project Structure

At runtime, MeshRender Studio uses these local folders:

- `projects/`: saved project JSON files
- `workspace/<project-id>/inputs/`: imported source files
- `workspace/<project-id>/mesh/`: generated VTU outputs
- `workspace/<project-id>/figures/`: rendered PNG outputs

These folders are intentionally excluded from Git so the public repository stays clean.

## Creating or Loading a Project

1. Click `New Project` to create a fresh project template.
2. Enter a project name in `Project Info`.
3. Use `Save Project` to store the current configuration.
4. Use the `Saved projects` dropdown and `Load` to reopen a saved setup.

Project saves preserve sources, views, render defaults, and output directory settings.

## Importing and Managing Sources

The `Sources` table defines what gets prepared and rendered.

- `Import Files` copies one or more local files into the project workspace and creates matching source rows.
- `Add Source Row` creates a manual row for an existing relative path.
- `Kind` can stay on `auto` or be set explicitly.
- `Views` accepts one or more comma-separated view names.
- `Figure Prefix` controls the output filename stem.

For Abaqus and AQWA workflows, `part_name`, `part_index`, and `structure_filter` remain available for fine-grained selection.

## Editing Views

The `Views` table defines camera presets reused by one or more sources.

- `Azimuth`, `Elevation`, and `Roll` are edited with synchronized sliders and number fields.
- All three angle fields use **degrees**.
- The slider range is `-180` to `180`.
- `Zoom` remains a numeric factor.
- `Parallel` toggles per-view parallel projection.

If you need a new preset, click `Add View` and then assign that view name from the `Sources` table.

## Zoom Insets

Use the `Zoom Insets` panel when you want one output image to contain:

- the full rendered mesh
- a highlighted crop region on that mesh
- an enlarged inset of the same region

Each inset is configured per source.

- `Enable inset` turns the layout on or off.
- `Target view` selects which rendered view receives the inset composition.
- `Crop box` uses normalized `x, y, width, height` coordinates in the range `0..1`.
- `Inset box` uses the same normalized coordinate format to place the enlarged crop.
- `Outline color` and `Outline width` control the callout box, inset frame, and connector line.

Coordinates are measured from the top-left corner of the final rendered image.

## Render Defaults

The `Render Defaults` section controls shared output style:

- image width and height
- background color
- surface color
- edge color
- line width
- surface opacity
- default parallel projection

Source-level render settings can still override shared defaults if you extend the saved JSON manually.

## Rendering Workflow

1. Import or define at least one source.
2. Confirm the project views and render defaults.
3. Click `Prepare + Render`.
4. Watch the `Run Controls` status and log output.
5. When the job completes, inspect images in `Results Gallery`.

For `.inp` and `.LIS` sources, MeshRender Studio first generates VTU meshes, then renders figures with ParaView. For `.vtu` and `.vtk` inputs, rendering uses the existing mesh directly.

## Saved Projects and Outputs

Saved projects store the configuration only. Generated meshes and figures remain in the project workspace and can be regenerated if needed.

The results area exposes:

- rendered PNG previews
- links to generated mesh artifacts

## Troubleshooting

- If ParaView shows as unavailable, verify `pvpython` is installed and discoverable.
- If a source row fails validation, confirm the file extension and input path.
- If rendering completes without images, verify that each source references at least one existing view name.
- If imported files are large, keep the public Git repo clean by leaving runtime outputs inside ignored `projects/` and `workspace/` folders only.

## Author

- Shuijin Li
- shuijinli@outlook.com
