from __future__ import annotations

import argparse
from pathlib import Path

from ingest.pipeline import STAGES, run_pipeline


def _parse_stages(value: str) -> tuple[str, ...]:
    stages = tuple(stage.strip() for stage in value.split(",") if stage.strip())
    return stages or STAGES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ingest", description="LennyVerse local ingestion CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run local ingestion over input markdown files.")
    run_parser.add_argument("--input", default="data/inputs", help="Input directory of markdown files.")
    run_parser.add_argument(
        "--output",
        default="data/ingest-output",
        help="Output directory for ingestion artifacts.",
    )
    run_parser.add_argument("--since", default=None, help="ISO date/time filter for published_at.")
    run_parser.add_argument("--limit", type=int, default=None, help="Max number of documents.")
    run_parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess documents even when checksum is unchanged.",
    )
    run_parser.add_argument(
        "--stages",
        default="parse,chunk,embed,extract,load,project",
        help="Comma-separated stages to run.",
    )

    backfill_parser = subparsers.add_parser(
        "backfill", help="Backfill all local documents of a source type."
    )
    backfill_parser.add_argument("--source", choices=["newsletter", "podcast"], required=True)
    backfill_parser.add_argument("--input", default="data/inputs")
    backfill_parser.add_argument("--output", default="data/ingest-output")
    backfill_parser.add_argument("--stages", default="parse,chunk,embed,extract,load,project")
    backfill_parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess documents even when checksum is unchanged.",
    )

    rebuild_graph_parser = subparsers.add_parser(
        "rebuild-graph", help="Rebuild graph projection markers from canonical artifacts."
    )
    rebuild_graph_parser.add_argument("--output", default="data/ingest-output")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        result = run_pipeline(
            input_dir=Path(args.input),
            output_dir=Path(args.output),
            since=args.since,
            limit=args.limit,
            stages=_parse_stages(args.stages),
            force=args.force,
        )
        print(result)
        return 0

    if args.command == "backfill":
        result = run_pipeline(
            input_dir=Path(args.input),
            output_dir=Path(args.output),
            stages=_parse_stages(args.stages),
            source_filter=args.source,
            force=args.force,
        )
        print(result)
        return 0

    if args.command == "rebuild-graph":
        output_dir = Path(args.output)
        marker = output_dir / "graph_rebuild_requested.txt"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("Graph rebuild requested for local manual ingestion.\n", encoding="utf-8")
        print({"status": "ok", "marker": str(marker)})
        return 0

    parser.error("Unknown command")
    return 1

