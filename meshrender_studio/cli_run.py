from __future__ import annotations

"""
Convenience runner for batch mesh preparation and ParaView rendering.
"""

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from pathlib import Path
import subprocess
import sys

from meshrender_studio.core import find_pvpython


PACKAGE_DIR = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run batch mesh preparation and ParaView rendering with one command.",
    )
    parser.add_argument(
        "--config",
        help="JSON config file. Defaults to ./mesh_batch_config.json if present.",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Source name, figure prefix, or input filename. Repeat as needed.",
    )
    parser.add_argument(
        "--view",
        action="append",
        dest="views",
        help="View name to render. Repeat as needed.",
    )
    parser.add_argument(
        "--pvpython",
        help="Path to pvpython. Defaults to PVPYTHON, PATH, or the known ParaView app path.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only prepare mesh files and skip rendering.",
    )
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Only render figures and skip mesh preparation.",
    )
    return parser


def append_repeated_args(command: list[str], flag: str, values: list[str] | None) -> None:
    if not values:
        return
    for value in values:
        command.extend([flag, value])


def main() -> int:
    args = build_parser().parse_args()
    if args.prepare_only and args.render_only:
        raise SystemExit("Choose at most one of --prepare-only or --render-only.")

    if not args.render_only:
        prepare_cmd = [sys.executable, str(PACKAGE_DIR / "cli_prepare.py")]
        if args.config:
            prepare_cmd.extend(["--config", args.config])
        append_repeated_args(prepare_cmd, "--source", args.sources)
        subprocess.run(prepare_cmd, check=True)

    if not args.prepare_only:
        pvpython = find_pvpython(args.pvpython)
        render_cmd = [pvpython, str(PACKAGE_DIR / "cli_render.py")]
        if args.config:
            render_cmd.extend(["--config", args.config])
        append_repeated_args(render_cmd, "--source", args.sources)
        append_repeated_args(render_cmd, "--view", args.views)
        subprocess.run(render_cmd, check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
