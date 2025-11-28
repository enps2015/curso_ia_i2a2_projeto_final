#!/usr/bin/env python3
"""Converte os indicadores consolidados do SIOPS (Bronze) para parquet Silver."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

DEFAULT_INPUT = Path("data/bronze/siops/siops_indicadores_rmb_2018_2025.csv")
DEFAULT_MUNICIPIOS = Path("config/rmb_municipios.csv")
DEFAULT_OUTPUT = Path("data/silver/siops/indicadores.parquet")

# Mapeia código do indicador → (nome da coluna, fator de escala)
# fator = 1.0 → valor per capita; fator = 100.0 → percentual
INDICATOR_CONFIG: Dict[str, Tuple[str, float]] = {
    "1.3": ("pct_transferencias_sus_recursos", 100.0),
    "1.6": ("pct_receita_impostos_transf", 100.0),
    "2.1": ("despesa_saude_pc", 1.0),
    "2.2": ("pct_despesa_pessoal_saude", 100.0),
    "2.3": ("pct_despesa_medicamentos_saude", 100.0),
    "2.4": ("pct_despesa_terceiros_pj_saude", 100.0),
    "2.5": ("pct_despesa_investimentos_saude", 100.0),
    "2.6": ("pct_despesa_privado_sem_fins", 100.0),
    "3.1": ("pct_transferencias_sobre_despesa", 100.0),
    "3.2": ("pct_receita_propria_asps", 100.0),
}


def load_municipios(path: Path) -> Dict[str, Tuple[str, str]]:
    df = pd.read_csv(path, dtype={"ibge_code": "string"})
    df = df[df["is_rmb"] == 1]
    df["ibge_code"] = df["ibge_code"].str.zfill(7)
    mapping: Dict[str, Tuple[str, str]] = {}
    for _, row in df.iterrows():
        code7 = row["ibge_code"]
        code6 = code7[:-1]
        mapping[code6] = (code7, row["name"].upper())
        mapping[code7] = (code7, row["name"].upper())
    return mapping


def normalize_indicator_code(value: float) -> str:
    code = f"{value:.1f}".rstrip("0").rstrip(".")
    return code


def build_siops_silver(input_path: Path, municipios_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    df["codigo"] = df["numero_indicador"].map(normalize_indicator_code)
    df = df[df["codigo"].isin(INDICATOR_CONFIG)]

    df["cod_mun"] = df["cod_mun"].astype(str).str.zfill(6)
    df["ano"] = df["ano"].astype(int)

    df["valor_calc"] = df["numerador"] / df["denominador"]
    df.loc[df["denominador"].isna() | (df["denominador"] == 0), "valor_calc"] = np.nan

    scale = df["codigo"].map({code: scale for code, (_, scale) in INDICATOR_CONFIG.items()})
    df["valor_calc"] = df["valor_calc"] * scale

    pivot = (
        df.pivot_table(
            index=["cod_mun", "ano"],
            columns="codigo",
            values="valor_calc",
            aggfunc="first",
        )
        .rename(columns={code: col for code, (col, _) in INDICATOR_CONFIG.items()})
        .reset_index()
        .sort_values(["cod_mun", "ano"])
    )

    # Reordena colunas para deixar métricas em ordem crescente do código
    ordered_cols = ["cod_mun", "ano"] + [cfg[0] for cfg in INDICATOR_CONFIG.values()]
    pivot = pivot[ordered_cols]

    metric_cols = [cfg[0] for cfg in INDICATOR_CONFIG.values()]
    pivot[metric_cols] = pivot[metric_cols].round(2)

    municipios = load_municipios(municipios_path)
    mapped = pivot["cod_mun"].map(municipios)
    if mapped.isna().any():
        missing = pivot.loc[mapped.isna(), "cod_mun"].unique()
        raise ValueError(f"Códigos sem mapeamento de município: {missing}")

    pivot["cod_mun"] = mapped.map(lambda x: x[0])
    pivot["municipio"] = mapped.map(lambda x: x[1])

    cols = ["cod_mun", "municipio", "ano"] + [c for c in pivot.columns if c not in {"cod_mun", "municipio", "ano"}]
    pivot = pivot[cols]

    return pivot.reset_index(drop=True)


def save_parquet(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False, compression="snappy")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="CSV de indicadores SIOPS já consolidado")
    parser.add_argument("--municipios", type=Path, default=DEFAULT_MUNICIPIOS, help="CSV com códigos IBGE da RMB")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="Parquet de saída na camada Silver")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = build_siops_silver(args.input, args.municipios)
    save_parquet(df, args.out)
    print(f"[OK] SIOPS Silver gerado: {len(df)} linhas → {args.out}")


if __name__ == "__main__":
    main()
