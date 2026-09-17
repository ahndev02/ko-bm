"""CLI entrypoint: kobalt-eval run|score|compare."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kobalt-eval", description="KoBALT-700 benchmark evaluation harness")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="Run an evaluation from a run config")
    r.add_argument("--config", required=True, help="Path to run.yaml (YAML preferred) or run.json")
    r.add_argument("--limit", type=int, default=None, help="Evaluate only the first N items")
    r.add_argument("--resume", default=None, metavar="RUN_DIR", help="Resume an existing run directory")
    r.add_argument("--out", default=None, help="Output run directory (default: runs/<timestamp>-<model>)")

    s = sub.add_parser("score", help="Score a run directory (no model calls)")
    s.add_argument("run_dir", help="Run directory containing predictions.jsonl")

    c = sub.add_parser("compare", help="Compare multiple run directories")
    c.add_argument("run_dirs", nargs="+", help="Run directories to compare")
    c.add_argument("--out", default=None, help="Write table to file (.md -> markdown, .json -> JSON); default stdout")
    return p


def cmd_run(args: argparse.Namespace) -> int:
    from kobalt_eval.config import load_config
    from kobalt_eval.runner import default_run_dir_name, run_eval

    config = load_config(args.config)
    if args.resume:
        run_dir = Path(args.resume)
    elif args.out:
        run_dir = Path(args.out)
    else:
        run_dir = Path("runs") / default_run_dir_name(config.backend.model)
    run_eval(config, run_dir, limit=args.limit, resume=bool(args.resume))
    print(f"run complete: {run_dir}")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    from kobalt_eval.scoring import score_run

    results = score_run(args.run_dir)
    print(f"scored {args.run_dir}: accuracy={results.get('accuracy', 0.0):.4f} n={results.get('num_items', 0)}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from kobalt_eval.reporting import compare_and_write

    text = compare_and_write(args.run_dirs, out=args.out)
    if args.out:
        print(f"comparison written to {args.out}")
    else:
        print(text, end="" if text.endswith("\n") else "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return cmd_run(args)
        if args.command == "score":
            return cmd_score(args)
        if args.command == "compare":
            return cmd_compare(args)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
