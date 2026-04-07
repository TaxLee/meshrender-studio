from __future__ import annotations

"""
Batch mesh preparation for ParaView-friendly VTU files.
"""

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

from meshrender_studio.core import load_batch_config
from meshrender_studio.core import prepare_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse configured mesh sources and export VTU files.",
    )
    parser.add_argument(
        "--config",
        help="JSON config file. Defaults to ./mesh_batch_config.json if present.",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Source name, figure prefix, or input filename to prepare. Repeat as needed.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_batch_config(args.config)
    outputs = prepare_sources(config, args.sources)
    config_hint = args.config or "mesh_batch_config.json"

    print("\nPrepared mesh files:")
    for path in outputs:
        print(f"  {path}")

    print("\nNext step:")
    print(f"  pvpython -m meshrender_studio.cli_render --config {config_hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
