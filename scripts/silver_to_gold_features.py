#!/usr/bin/env python3
"""Constrói o conjunto Gold anual agregando as camadas Silver (serviço, qualidade, clima, saúde e finanças)."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

DEFAULT_MUNICIPIOS = Path("config/rmb_municipios.csv")
DEFAULT_OUT_PARQUET = Path("data/gold/gold_features_ano.parquet")
DEFAULT_OUT_CSV = Path("data/gold/gold_features_ano.csv")

QUALITY_PARAMS = (
    "cloro_residual_livre",
    "turbidez",
    "ph",
    "coliformes_totais",
    "escherichia_coli",
    "fluoreto",
    "cor",
)

# Atribui cada estação meteorológica INMET aos municípios da RMB mais próximos.
STATION_TO_MUNICIPALITIES = {
    "A201": ("1501402", "1500800", "1504422", "1501501"),  # Belém + eixo Ananindeua/Marituba/Benevides
    "A202": ("1502400", "1506500", "1506351"),              # Castanhal + Santa Izabel + Santa Bárbara
    "A227": ("1501303",),                                      # Soure como proxy para Barcarena
}


@dataclass(frozen=True)
class Municipio:
    code: str
    name: str


def load_municipios(path: Path) -> Dict[str, Municipio]:
    df = pd.read_csv(path, dtype={"ibge_code": "string"})
    df = df[df["is_rmb"] == 1]
    df["ibge_code"] = df["ibge_code"].str.zfill(7)

    mapping: Dict[str, Municipio] = {}
    for _, row in df.iterrows():
        code7 = row["ibge_code"]
        code6 = code7[:-1]
        muni = Municipio(code=code7, name=row["name"].upper())
        mapping[code7] = muni
        mapping[code6] = muni
    return mapping


def normalize_cod_mun(series: Iterable, mapping: Dict[str, Municipio]) -> pd.Series:
    def _normalize(value: object) -> Optional[str]:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        text = str(value).strip()
        if not text:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return None
        if digits in mapping:
            return mapping[digits].code
        if len(digits) > 7:
            digits = digits[:7]
            if digits in mapping:
                return mapping[digits].code
        digits6 = digits[:6]
        if digits6 in mapping:
            return mapping[digits6].code
        padded = digits.zfill(7)
        return padded if padded in mapping else None

    normalized = pd.Series(series, dtype="object").map(_normalize)
    return normalized


def aggregate_sih(mapping: Dict[str, Municipio]) -> pd.DataFrame:
    dataset = ds.dataset("data/silver/sih", format="parquet", partitioning="hive")
    df = dataset.to_table().to_pandas()
    df["cod_mun"] = normalize_cod_mun(df["cod_mun"], mapping)
    df = df.dropna(subset=["cod_mun"]).copy()
    df["ano"] = df["ano"].astype(int)

    agg = (
        df.groupby(["cod_mun", "ano"], as_index=False)
        .agg(
            internacoes_total=("internacoes_total", "sum"),
            internacoes_hidricas=("internacoes_hidricas", "sum"),
            dias_perm_total=("dias_perm_total", "sum"),
            dias_perm_hidricas=("dias_perm_hidricas", "sum"),
            valor_total=("valor_total", "sum"),
            valor_hidricas=("valor_hidricas", "sum"),
        )
    )
    return agg


def aggregate_sisagua(mapping: Dict[str, Municipio]) -> pd.DataFrame:
    dataset = ds.dataset("data/silver/sisagua", format="parquet", partitioning="hive")
    df = dataset.to_table().to_pandas()
    df["cod_mun"] = normalize_cod_mun(df["cod_mun"], mapping)
    df = df.dropna(subset=["cod_mun"]).copy()
    df["ano"] = df["ano"].astype(int)
    df["amostras_total"] = df["amostras_total"].fillna(0.0)
    df["amostras_conformes"] = df["amostras_conformes"].fillna(0.0)
    df["amostras_nao_conformes"] = df["amostras_nao_conformes"].fillna(0.0)
    df["percentil_95"] = df["percentil_95"].astype(float)

    grouped = (
        df.groupby(["cod_mun", "ano", "parametro"], as_index=False)
        .agg(
            amostras_total=("amostras_total", "sum"),
            amostras_conformes=("amostras_conformes", "sum"),
            amostras_nao_conformes=("amostras_nao_conformes", "sum"),
            percentil_95=("percentil_95", "mean"),
        )
    )
    grouped["pct_conformes_param"] = np.where(
        grouped["amostras_total"] > 0,
        grouped["amostras_conformes"] / grouped["amostras_total"] * 100,
        np.nan,
    )

    # Agregados globais (todas as variáveis)
    global_agg = (
        grouped.groupby(["cod_mun", "ano"], as_index=False)
        .agg(
            sisagua_amostras_total=("amostras_total", "sum"),
            sisagua_amostras_conformes=("amostras_conformes", "sum"),
            sisagua_amostras_nao_conformes=("amostras_nao_conformes", "sum"),
        )
    )
    global_agg["pct_conformes_global"] = np.where(
        global_agg["sisagua_amostras_total"] > 0,
        global_agg["sisagua_amostras_conformes"] / global_agg["sisagua_amostras_total"] * 100,
        np.nan,
    )

    # Percentual de conformidade por parâmetro (somente os monitorados)
    param_pct = (
        grouped[grouped["parametro"].isin(QUALITY_PARAMS)]
        .pivot_table(
            index=["cod_mun", "ano"],
            columns="parametro",
            values="pct_conformes_param",
            aggfunc="first",
        )
    )
    param_pct.columns = [f"pct_conformes_{param}" for param in param_pct.columns]

    percentil = (
        grouped[grouped["parametro"].isin({"turbidez", "cloro_residual_livre", "ph", "fluoreto"})]
        .pivot_table(
            index=["cod_mun", "ano"],
            columns="parametro",
            values="percentil_95",
            aggfunc="first",
        )
    )
    percentil.columns = [f"percentil95_{param}" for param in percentil.columns]

    result = (
        global_agg.set_index(["cod_mun", "ano"])
        .join(param_pct, how="left")
        .join(percentil, how="left")
        .reset_index()
    )
    return result


def aggregate_inmet(mapping: Dict[str, Municipio]) -> pd.DataFrame:
    dataset = ds.dataset("data/silver/inmet", format="parquet", partitioning="hive")
    columns = ["estacao", "ano", "timestamp_utc", "chuva_mm", "temp_c", "umid_rel_pct", "vento_vel_ms"]
    df = dataset.to_table(columns=columns).to_pandas()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=False)
    df["chuva_mm"] = df["chuva_mm"].fillna(0.0)
    df["temp_c"] = df["temp_c"].astype(float)
    df["umid_rel_pct"] = df["umid_rel_pct"].astype(float)
    df["vento_vel_ms"] = df["vento_vel_ms"].astype(float)

    df = df.dropna(subset=["estacao", "ano"])
    df["ano"] = df["ano"].astype(int)

    # Dias com temperatura extrema (>= 32ºC)
    daily_max = (
        df.dropna(subset=["temp_c"])
        .assign(data=df["timestamp_utc"].dt.date)
        .groupby(["estacao", "ano", "data"], as_index=False)["temp_c"].max()
    )
    heat_days = (
        daily_max[daily_max["temp_c"] >= 32]
        .groupby(["estacao", "ano"])
        .size()
        .to_dict()
    )

    station_year = (
        df.groupby(["estacao", "ano"], as_index=False)
        .agg(
            chuva_total_mm=("chuva_mm", "sum"),
            chuva_media_mm=("chuva_mm", "mean"),
            temp_media_c=("temp_c", "mean"),
            temp_max_c=("temp_c", "max"),
            temp_min_c=("temp_c", "min"),
            umid_rel_media_pct=("umid_rel_pct", "mean"),
            vento_vel_media_ms=("vento_vel_ms", "mean"),
        )
    )
    station_year["dias_calor_extremo"] = station_year.apply(
        lambda row: heat_days.get((row["estacao"], row["ano"]), 0), axis=1
    )

    records: List[Dict[str, object]] = []
    for row in station_year.itertuples(index=False):
        municipios = STATION_TO_MUNICIPALITIES.get(row.estacao)
        if not municipios:
            continue
        for cod in municipios:
            if cod not in mapping:
                continue
            records.append(
                {
                    "cod_mun": mapping[cod].code,
                    "ano": int(row.ano),
                    "chuva_total_mm": float(row.chuva_total_mm) if row.chuva_total_mm is not None else np.nan,
                    "chuva_media_mm": float(row.chuva_media_mm) if row.chuva_media_mm is not None else np.nan,
                    "temp_media_c": float(row.temp_media_c) if row.temp_media_c is not None else np.nan,
                    "temp_max_c": float(row.temp_max_c) if row.temp_max_c is not None else np.nan,
                    "temp_min_c": float(row.temp_min_c) if row.temp_min_c is not None else np.nan,
                    "umid_rel_media_pct": float(row.umid_rel_media_pct) if row.umid_rel_media_pct is not None else np.nan,
                    "vento_vel_media_ms": float(row.vento_vel_media_ms) if row.vento_vel_media_ms is not None else np.nan,
                    "dias_calor_extremo": int(row.dias_calor_extremo),
                }
            )
    clima_df = pd.DataFrame.from_records(records)
    return clima_df


def aggregate_siops(mapping: Dict[str, Municipio]) -> pd.DataFrame:
    df = pd.read_parquet("data/silver/siops/indicadores.parquet")
    df["cod_mun"] = normalize_cod_mun(df["cod_mun"], mapping)
    df = df.dropna(subset=["cod_mun"]).copy()
    df["ano"] = df["ano"].astype(int)
    df = df.drop(columns=["municipio"], errors="ignore")
    return df


def aggregate_snis(mapping: Dict[str, Municipio]) -> pd.DataFrame:
    df = pd.read_csv("data/gold/snis_rmb_indicadores_v2.csv")
    df["cod_mun"] = normalize_cod_mun(df["cod_mun"], mapping)
    df = df.dropna(subset=["cod_mun"]).copy()
    df["ano"] = df["ano"].astype(int)
    rename = {
        "idx_atend_agua_total": "idx_atend_agua_total",
        "idx_atend_agua_urbano": "idx_atend_agua_urbano",
        "idx_coleta_esgoto": "idx_coleta_esgoto",
        "idx_tratamento_esgoto": "idx_tratamento_esgoto",
        "idx_hidrometracao": "idx_hidrometracao",
        "idx_perdas_distribuicao": "idx_perdas_distribuicao",
        "idx_perdas_lineares": "idx_perdas_lineares",
        "idx_perdas_por_ligacao": "idx_perdas_por_ligacao",
        "tarifa_media_agua": "tarifa_media_agua",
        "tarifa_media_esgoto": "tarifa_media_esgoto",
    }
    keep_cols = ["cod_mun", "ano"] + [col for col in rename if col in df.columns]
    return df[keep_cols]


def load_populacao(mapping: Dict[str, Municipio]) -> pd.DataFrame:
    df = pd.read_parquet("data/silver/ibge_populacao/populacao.parquet")
    df["cod_mun"] = normalize_cod_mun(df["cod_mun"], mapping)
    df = df.dropna(subset=["cod_mun"]).copy()
    df["ano"] = df["ano"].astype(int)
    df["populacao"] = df["populacao"].astype(float)
    return df


def build_base_frame(mapping: Dict[str, Municipio], anos: Sequence[int]) -> pd.DataFrame:
    municipios_unicos = sorted({municipio.code for municipio in mapping.values()})
    municipios_unicos = [code for code in municipios_unicos if len(code) == 7]
    index = pd.MultiIndex.from_product([municipios_unicos, anos], names=["cod_mun", "ano"])
    base = index.to_frame(index=False)
    base["municipio"] = base["cod_mun"].map(lambda code: mapping[code].name if code in mapping else np.nan)
    return base


def merge_all() -> pd.DataFrame:
    mapping = load_municipios(DEFAULT_MUNICIPIOS)

    sih = aggregate_sih(mapping)
    sisagua = aggregate_sisagua(mapping)
    clima = aggregate_inmet(mapping)
    siops = aggregate_siops(mapping)
    snis = aggregate_snis(mapping)
    populacao = load_populacao(mapping)

    anos = sorted({
        *sih.get("ano", pd.Series(dtype=int)).unique().tolist(),
        *sisagua.get("ano", pd.Series(dtype=int)).unique().tolist(),
        *clima.get("ano", pd.Series(dtype=int)).unique().tolist(),
        *siops.get("ano", pd.Series(dtype=int)).unique().tolist(),
        *snis.get("ano", pd.Series(dtype=int)).unique().tolist(),
        *populacao.get("ano", pd.Series(dtype=int)).unique().tolist(),
    })
    anos = [int(a) for a in anos if pd.notna(a)]
    base = build_base_frame(mapping, sorted(anos))

    data = (
        base
        .merge(populacao, on=["cod_mun", "ano"], how="left")
        .merge(snis, on=["cod_mun", "ano"], how="left")
        .merge(sisagua, on=["cod_mun", "ano"], how="left")
        .merge(clima, on=["cod_mun", "ano"], how="left")
        .merge(siops, on=["cod_mun", "ano"], how="left")
        .merge(sih, on=["cod_mun", "ano"], how="left")
        .sort_values(["cod_mun", "ano"])
    )

    data = data.rename(columns={"municipio": "municipio"})

    cols = ["cod_mun", "municipio", "ano"] + [col for col in data.columns if col not in {"cod_mun", "municipio", "ano"}]
    data = data[cols]

    # Derivados
    data["internacoes_total_10k"] = np.where(
        data["populacao"] > 0,
        data["internacoes_total"] / data["populacao"] * 10000,
        np.nan,
    )
    data["internacoes_hidricas_10k"] = np.where(
        data["populacao"] > 0,
        data["internacoes_hidricas"] / data["populacao"] * 10000,
        np.nan,
    )
    data["pct_internacoes_hidricas"] = np.where(
        data["internacoes_total"] > 0,
        data["internacoes_hidricas"] / data["internacoes_total"] * 100,
        np.nan,
    )
    data["valor_medio_internacao"] = np.where(
        data["internacoes_total"] > 0,
        data["valor_total"] / data["internacoes_total"],
        np.nan,
    )

    return data


def save_outputs(df: pd.DataFrame, parquet_path: Path, csv_path: Path) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(parquet_path, index=False, compression="snappy")
    df.to_csv(csv_path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--municipios", type=Path, default=DEFAULT_MUNICIPIOS, help="Lista de municípios alvo")
    parser.add_argument("--out-parquet", type=Path, default=DEFAULT_OUT_PARQUET, help="Arquivo parquet de saída")
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV, help="Arquivo CSV de saída")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global DEFAULT_MUNICIPIOS
    DEFAULT_MUNICIPIOS = args.municipios
    df = merge_all()
    save_outputs(df, args.out_parquet, args.out_csv)
    print(
        f"[OK] Dataset Gold anual gerado com {len(df)} linhas → {args.out_parquet} / {args.out_csv}"
    )


if __name__ == "__main__":
    main()
