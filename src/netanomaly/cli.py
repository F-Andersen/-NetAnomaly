"""Command-line entry point: netanomaly <command>."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import ExperimentConfig, compare_runs, run_all, stage_evaluate, stage_fit, stage_prepare


def _config(args: argparse.Namespace) -> ExperimentConfig:
    fraction = args.sample_fraction if args.mode == "sample" else None
    if args.mode == "sample" and fraction is None:
        raise SystemExit("--mode sample requires --sample-fraction")
    default_id = f"{args.mode}_seed{args.seed}" if fraction is None else f"sample_f{fraction:g}_seed{args.seed}"
    return ExperimentConfig(
        run_id=args.run_id or default_id, seed=args.seed, sample_fraction=fraction,
        lof_train_size=args.lof_train_size,
    )


def _add_experiment_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", choices=["full", "sample"], default="full")
    parser.add_argument("--sample-fraction", type=float, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--lof-train-size", type=int, default=100000)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="netanomaly")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("prepare", "clean the CSV files and create the splits"),
        ("fit", "fit on train and choose thresholds on validation"),
        ("evaluate", "evaluate once on test"),
        ("run", "prepare + fit + evaluate"),
    ):
        _add_experiment_args(commands.add_parser(name, help=help_text))

    compare = commands.add_parser("compare-runs", help="check that two runs give identical metrics")
    compare.add_argument("first")
    compare.add_argument("second")

    load = commands.add_parser("load-results", help="write experiment results to PostgreSQL")
    load.add_argument("--run-id", required=True)

    replay = commands.add_parser("replay", help="send recorded CSV/parquet flows to the API (not live capture)")
    replay.add_argument("--input", default="data/processed/full/test.parquet")
    replay.add_argument("--api-url", default="http://localhost:8000")
    replay.add_argument("--limit", type=int, default=5000)
    replay.add_argument("--batch-size", type=int, default=200)
    replay.add_argument("--delay", type=float, default=0.0, help="seconds to wait between batches")
    replay.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)

    if args.command == "compare-runs":
        result = compare_runs(Path("reports"), args.first, args.second)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["identical"] else 1
    if args.command == "load-results":
        from .results_loader import load_results

        print(json.dumps(load_results(args.run_id), ensure_ascii=False))
        return 0
    if args.command == "replay":
        from .replay import replay_file

        print(json.dumps(replay_file(args.input, args.api_url, args.limit, args.batch_size, args.delay, args.seed), ensure_ascii=False, indent=2))
        return 0

    cfg = _config(args)
    if args.command == "prepare":
        result = stage_prepare(cfg)
    elif args.command == "fit":
        stage_prepare(cfg)
        result = stage_fit(cfg)
    elif args.command == "evaluate":
        result = stage_evaluate(cfg)
    else:
        result = run_all(cfg)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
