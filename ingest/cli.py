from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from ingest.neo4j_projector import project_to_neo4j
from ingest.pipeline import STAGES, run_pipeline
from ingest.supabase_loader import fetch_projection_inputs

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
        force=True,
    )


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
        "rebuild-graph",
        help="Rebuild Neo4j graph projection from canonical Supabase data (clear + full project).",
    )
    rebuild_graph_parser.add_argument(
        "--output",
        default=None,
        metavar="DIR",
        help=argparse.SUPPRESS,
    )

    return parser


def main() -> int:
    _configure_logging()
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
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "backfill":
        result = run_pipeline(
            input_dir=Path(args.input),
            output_dir=Path(args.output),
            stages=_parse_stages(args.stages),
            source_filter=args.source,
            force=args.force,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "rebuild-graph":
        if args.output is not None:
            logger.warning(
                "--output is ignored for rebuild-graph; canonical rebuild uses Supabase and Neo4j only"
            )
        try:
            payload = fetch_projection_inputs()
        except Exception:
            logger.exception("Failed to read canonical data from Supabase")
            return 1
        try:
            result = project_to_neo4j(payload, clear_first=True)
        except Exception:
            logger.exception("Neo4j projection failed")
            return 1
        print(json.dumps(result, indent=2, default=str))
        return 0

    parser.error("Unknown command")
    return 1

