from __future__ import annotations

"""
Batch ParaView rendering for prepared mesh figures.
"""

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

from meshrender_studio.core import load_batch_config
from meshrender_studio.render_engine import render_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render configured mesh figures with ParaView.",
    )
    parser.add_argument(
        "--config",
        help="JSON config file. Defaults to ./mesh_batch_config.json if present.",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Source name, figure prefix, or input filename to render. Repeat as needed.",
    )
    parser.add_argument(
        "--view",
        action="append",
        dest="views",
        help="View name to render. Repeat as needed.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_batch_config(args.config)
    render_config(config, args.sources, args.views)
    print("Done.")


if __name__ == "__main__":
    main()
