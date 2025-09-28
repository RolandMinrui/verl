"""Turn-sorted BFCL multi-turn dataset writer."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Sequence

import pandas as pd

_ID_PATTERN = re.compile(r"base_(\d+)_turn_(\d+)_([0-9]+)")


def _parse_record_id(record_id: str) -> tuple[int, int, int]:
    """Return (base_index, turn_index, variant_index) parsed from a record id."""
    match = _ID_PATTERN.search(record_id)
    if not match:
        raise ValueError(f"Unable to parse turn metadata from record id: {record_id}")
    base_idx, turn_idx, variant_idx = match.groups()
    return int(base_idx), int(turn_idx), int(variant_idx)


def _sort_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Sort a BFCL multi-turn dataframe by turn, then base and variant."""
    metadata = df["id"].apply(
        lambda value: pd.Series(_parse_record_id(value), index=["_base", "_turn", "_variant"])
    )
    sortable = pd.concat([df.reset_index(drop=True), metadata], axis=1)
    ordered = sortable.sort_values(["_turn", "_base", "_variant", "id"]).drop(columns=["_base", "_turn", "_variant"])
    return ordered.reset_index(drop=True)


def _process_split(split: str, input_dir: Path, output_dir: Path) -> Path:
    """Sort one split and persist it to the output directory."""
    source_path = input_dir / f"{split}.parquet"
    if not source_path.exists():
        raise FileNotFoundError(f"Missing expected split: {source_path}")

    df = pd.read_parquet(source_path)
    sorted_df = _sort_dataframe(df)

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{split}.parquet"
    sorted_df.to_parquet(destination, index=False)
    return destination


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sort BFCL multi-turn parquet files by turn index.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/BFCL/multi-turn"),
        help="Directory containing the original parquet files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/BFCL/multi-turn-turn-sorted"),
        help="Where to write the turn-sorted parquet files.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=("train", "test"),
        help="Dataset splits to process.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    for split in args.splits:
        _process_split(split, args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
