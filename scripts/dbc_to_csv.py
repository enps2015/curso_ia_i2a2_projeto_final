#!/usr/bin/env python3
"""Conversor em lote de arquivos DBC (DATASUS) para CSV simples."""

import argparse
import tempfile
from pathlib import Path

import pandas as pd
from dbfread import DBF
from pyreaddbc import readdbc
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(description="Convert DBC files to CSV")
    parser.add_argument("--src", type=str, required=True, help="Source directory containing DBC files")
    parser.add_argument("--dst", type=str, required=True, help="Destination directory for CSV files")
    parser.add_argument("--encoding", type=str, default="iso-8859-1", help="Text encoding for string fields")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reprocess files even when the destination CSV already exists",
    )
    parser.add_argument(
        "--glob",
        type=str,
        default="*.dbc",
        help="Glob pattern used to select input files (default: *.dbc)",
    )
    args = parser.parse_args()

    src_path = Path(args.src)
    dst_path = Path(args.dst)
    dst_path.mkdir(parents=True, exist_ok=True)

    dbc_files = sorted(src_path.glob(args.glob))
    if not dbc_files:
        print(f"No DBC files found in {src_path}")
        return

    for path in tqdm(dbc_files, desc="Converting DBC to CSV"):
        try:
            output_filename = dst_path / f"{path.stem}.csv"
            if output_filename.exists() and not args.overwrite:
                continue

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_dbf = Path(tmpdir) / f"{path.stem}.dbf"
                # Converte o DBC comprimido usando a biblioteca oficial do DATASUS.
                readdbc.dbc2dbf(str(path), str(tmp_dbf))

                table = DBF(
                    str(tmp_dbf),
                    encoding=args.encoding,
                    char_decode_errors="ignore",
                )
                dataframe = pd.DataFrame(iter(table))

            dataframe.to_csv(output_filename, index=False)
        except Exception as exc:
            print(f"Error converting {path}: {exc}")

if __name__ == "__main__":
    main()
