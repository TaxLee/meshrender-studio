from __future__ import annotations

from pathlib import Path
from math import hypot

from PIL import Image
from PIL import ImageDraw


def to_pixel_bounds(rect: list[float], image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = image_size
    left = max(0, min(width - 1, int(round(rect[0] * width))))
    top = max(0, min(height - 1, int(round(rect[1] * height))))
    right = max(left + 1, min(width, int(round((rect[0] + rect[2]) * width))))
    bottom = max(top + 1, min(height, int(round((rect[1] + rect[3]) * height))))
    return left, top, right, bottom


def to_outline_bounds(rect: list[float], image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    left, top, right, bottom = to_pixel_bounds(rect, image_size)
    return left, top, right - 1, bottom - 1


def to_rgb8(color: list[float]) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(round(channel * 255)))) for channel in color)


def closest_connector(
    focus_bounds: tuple[int, int, int, int],
    inset_bounds: tuple[int, int, int, int],
) -> tuple[tuple[int, int], tuple[int, int]]:
    focus_corners = [
        (focus_bounds[0], focus_bounds[1]),
        (focus_bounds[2], focus_bounds[1]),
        (focus_bounds[0], focus_bounds[3]),
        (focus_bounds[2], focus_bounds[3]),
    ]
    inset_corners = [
        (inset_bounds[0], inset_bounds[1]),
        (inset_bounds[2], inset_bounds[1]),
        (inset_bounds[0], inset_bounds[3]),
        (inset_bounds[2], inset_bounds[3]),
    ]
    return min(
        (
            (focus_corner, inset_corner)
            for focus_corner in focus_corners
            for inset_corner in inset_corners
        ),
        key=lambda pair: hypot(pair[0][0] - pair[1][0], pair[0][1] - pair[1][1]),
    )


def compose_zoom_inset(image_path: Path, zoom_inset: dict) -> None:
    with Image.open(image_path) as image:
        base = image.convert("RGB")

    crop_bounds = to_pixel_bounds(zoom_inset["crop_box"], base.size)
    inset_bounds = to_pixel_bounds(zoom_inset["inset_box"], base.size)
    crop_outline = to_outline_bounds(zoom_inset["crop_box"], base.size)
    inset_outline = to_outline_bounds(zoom_inset["inset_box"], base.size)

    crop_image = base.crop(crop_bounds)
    inset_size = (
        inset_bounds[2] - inset_bounds[0],
        inset_bounds[3] - inset_bounds[1],
    )
    zoomed = crop_image.resize(inset_size, Image.Resampling.LANCZOS)

    composed = base.copy()
    composed.paste(zoomed, inset_bounds[:2])

    outline_color = to_rgb8(zoom_inset["stroke_color"])
    line_width = max(1, int(round(float(zoom_inset["stroke_width"]))))
    draw = ImageDraw.Draw(composed)
    draw.rectangle(crop_outline, outline=outline_color, width=line_width)
    draw.rectangle(inset_outline, outline=outline_color, width=line_width)
    line_start, line_end = closest_connector(crop_outline, inset_outline)
    draw.line([line_start, line_end], fill=outline_color, width=line_width)

    composed.save(image_path)
