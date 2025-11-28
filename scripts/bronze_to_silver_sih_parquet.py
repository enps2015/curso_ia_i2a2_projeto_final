#!/usr/bin/env python3
"""Converte os CSVs do SIH (convertidos de DBC) em Parquet Silver agregando por município/mês."""

from __future__ import annotations

import argparse
import shutil
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PARQUET_SCHEMA = pa.schema(
    [
        ("cod_mun", pa.string()),
        ("municipio", pa.string()),
        ("ano", pa.int32()),
        ("mes", pa.int32()),
        ("internacoes_total", pa.int64()),
        ("internacoes_hidricas", pa.int64()),
        ("dias_perm_total", pa.float64()),
        ("dias_perm_hidricas", pa.float64()),
        ("valor_total", pa.float64()),
        ("valor_hidricas", pa.float64()),
    ]
)

# Conjunto de CIDs considerados doenças de veiculação hídrica (principal)
TARGET_CID_PREFIXES = {f"A0{i}" for i in range(10)}  # A00-A09
TARGET_CID_PREFIXES.add("A09")  # reforça limite superior
TARGET_CID_PREFIX_EXTRA = ("E86",)  # desidratação

USECOLS = [
    "ANO_CMPT",
    "MES_CMPT",
    "MUNIC_RES",
    "DIAG_PRINC",
    "DIAS_PERM",
    "VAL_TOT",
]


def normalize_name(text: str) -> str:
    """Remove acentos e coloca em maiúsculas para padronização."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return normalized.upper()


def load_municipios(path: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Cria dicionários para mapear códigos (6 ou 7 dígitos) para código IBGE e nome normalizado."""
    df = pd.read_csv(path, dtype={"ibge_code": "string"})
    if df.empty:
        raise SystemExit("CSV de municípios está vazio.")

    code_to_ibge: Dict[str, str] = {}
    code_to_name: Dict[str, str] = {}
    for _, row in df.iterrows():
        code7 = str(row["ibge_code"]).strip().zfill(7)
        name = normalize_name(str(row["name"]))
        code6 = code7[:-1]

        for key in {code7, code6}:
            code_to_ibge[key] = code7
            code_to_name[key] = name
    return code_to_ibge, code_to_name


def normalize_cid(value: str | float | int | None) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip().upper().replace(".", "")
    return text


def is_target_cid(cid: str) -> bool:
    if not cid:
        return False
    if cid[:3] in TARGET_CID_PREFIXES:
        return True
    return any(cid.startswith(prefix) for prefix in TARGET_CID_PREFIX_EXTRA)


def clean_municipio_code(series: pd.Series) -> pd.Series:
    """Mantém apenas dígitos e retorna código com 6 ou 7 dígitos."""
    digits = series.fillna("").astype(str).str.replace(r"[^0-9]", "", regex=True)
    has_seven = digits.str.len() >= 7
    digits.loc[has_seven] = digits.loc[has_seven].str[:7]
    digits.loc[~has_seven] = digits.loc[~has_seven].str.zfill(6)
    return digits


def write_partitioned(df: pd.DataFrame, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)

    for (ano, mes), group in df.groupby(["ano", "mes"], dropna=False):
        partition_dir = out_dir / f"ano={int(ano)}" / f"mes={int(mes)}"
        partition_dir.mkdir(parents=True, exist_ok=True)

        table = pa.Table.from_pandas(group, schema=PARQUET_SCHEMA, preserve_index=False, safe=False)
        pq.write_table(table, partition_dir / "data.parquet", compression="snappy")


def aggregate_chunks(
    csv_path: Path,
    code_to_ibge: Dict[str, str],
    code_to_name: Dict[str, str],
    chunksize: int,
) -> Iterable[pd.DataFrame]:
    for chunk in pd.read_csv(
        csv_path,
        usecols=USECOLS,
        dtype=str,
        chunksize=chunksize,
        low_memory=False,
    ):
        chunk = chunk.dropna(subset=["ANO_CMPT", "MES_CMPT", "MUNIC_RES"])
        if chunk.empty:
            continue

        chunk["cod_lookup"] = clean_municipio_code(chunk["MUNIC_RES"])
        mask_valid = chunk["cod_lookup"].isin(code_to_ibge)
        chunk = chunk.loc[mask_valid].copy()
        if chunk.empty:
            continue

        chunk["cod_mun"] = chunk["cod_lookup"].map(code_to_ibge)
        chunk["municipio"] = chunk["cod_lookup"].map(code_to_name)
        chunk["ano"] = pd.to_numeric(chunk["ANO_CMPT"], errors="coerce").astype("Int64")
        chunk["mes"] = pd.to_numeric(chunk["MES_CMPT"], errors="coerce").astype("Int64")
        chunk = chunk.dropna(subset=["ano", "mes"])
        if chunk.empty:
            continue

        chunk["cid_principal"] = chunk["DIAG_PRINC"].map(normalize_cid)
        chunk["flag_hidrica"] = chunk["cid_principal"].map(is_target_cid).astype(int)

        chunk["dias_perm"] = pd.to_numeric(chunk["DIAS_PERM"], errors="coerce").fillna(0).astype(float)
        chunk["valor_total"] = pd.to_numeric(chunk["VAL_TOT"], errors="coerce").fillna(0.0)

        chunk["internacoes_total"] = 1
        chunk["internacoes_hidricas"] = chunk["flag_hidrica"]
        chunk["dias_perm_hidricas"] = chunk["dias_perm"] * chunk["flag_hidrica"]
        chunk["valor_hidricas"] = chunk["valor_total"] * chunk["flag_hidrica"]

        agg = (
            chunk.groupby(["cod_mun", "municipio", "ano", "mes"], dropna=False)
            .agg(
                internacoes_total=("internacoes_total", "sum"),
                internacoes_hidricas=("internacoes_hidricas", "sum"),
                dias_perm_total=("dias_perm", "sum"),
                dias_perm_hidricas=("dias_perm_hidricas", "sum"),
                valor_total=("valor_total", "sum"),
                valor_hidricas=("valor_hidricas", "sum"),
            )
            .reset_index()
        )

        yield agg


def process_directory(
    csv_dir: Path,
    municipios_csv: Path,
    out_dir: Path,
    chunksize: int,
) -> None:
    code_to_ibge, code_to_name = load_municipios(municipios_csv)

    csv_files = sorted(csv_dir.glob("RDPA*.csv"))
    if not csv_files:
        raise SystemExit(f"Nenhum CSV encontrado em {csv_dir} (execute o conversor DBC → CSV antes).")

    partial_results = []
    for csv_path in csv_files:
        print(f"[SIH] Processando {csv_path.name}...")
        for agg in aggregate_chunks(csv_path, code_to_ibge, code_to_name, chunksize):
            partial_results.append(agg)

    if not partial_results:
        raise SystemExit("Nenhum registro do SIH foi agregado. Verifique filtros e dados de entrada.")

    combined = pd.concat(partial_results, ignore_index=True)
    final_df = (
        combined.groupby(["cod_mun", "municipio", "ano", "mes"], dropna=False)
        .sum(numeric_only=True)
        .reset_index()
        .sort_values(["cod_mun", "ano", "mes"])
    )

    # Garante tipos inteiros quando possível
    for col in ["internacoes_total", "internacoes_hidricas"]:
        final_df[col] = final_df[col].astype("int64")

    final_df["ano"] = final_df["ano"].astype("int32")
    final_df["mes"] = final_df["mes"].astype("int32")
    final_df["cod_mun"] = final_df["cod_mun"].astype(str)

    write_partitioned(final_df, out_dir)
    print(
        f"[OK] SIH Silver gerado: {len(final_df)} linhas agregadas em {out_dir} (particionado por ano/mes)."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Agrega dados do SIH (CSV) em Parquet Silver.")
    parser.add_argument(
        "--csv-dir",
        default="data/bronze/sih/csv",
        help="Diretório com os CSVs convertidos do SIH",
    )
    parser.add_argument(
        "--municipios",
        default="config/rmb_municipios.csv",
        help="CSV com a lista de municípios alvo",
    )
    parser.add_argument("--out-dir", default="data/silver/sih", help="Diretório de saída para o Silver")
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Tamanho do chunk ao ler os CSVs (ajuste se necessário)",
    )
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir)
    municipios_csv = Path(args.municipios)
    out_dir = Path(args.out_dir)

    if not csv_dir.exists():
        raise SystemExit(f"Diretório inexistente: {csv_dir}")
    if not municipios_csv.exists():
        raise SystemExit(f"Arquivo de municípios não encontrado: {municipios_csv}")

    process_directory(csv_dir, municipios_csv, out_dir, args.chunksize)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
