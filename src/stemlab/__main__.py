"""A small headless entry point; desktop interfaces can reuse application.py."""

import argparse
import sys
from pathlib import Path

from stemlab.application import run_experiment
from stemlab.experiments.config import load_experiment
from stemlab.experiments.results import save_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a validated STEMLab numerical experiment")
    parser.add_argument("configuration", type=Path, help="version-1 experiment JSON")
    parser.add_argument("--output", required=True, type=Path, help="new result JSON path; existing files are preserved")
    args = parser.parse_args(argv)
    try:
        result = run_experiment(load_experiment(args.configuration))
        save_result(result, args.output)
    except (OSError, ValueError, OverflowError) as exc:
        print(f"stemlab: {exc}", file=sys.stderr)
        return 1
    print(f"Saved {len(result.history)} samples to {args.output}; analytical validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
