#!/usr/bin/env python3
"""Converte os CSVs mensais do SISAGUA (camada Bronze) para Parquet particionado."""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


# Limite superior por parâmetro segundo Portaria GM/MS nº 888/2021
SINGLE_BOUND_THRESHOLDS = {
    "turbidez": 5.0,
    "cor": 15.0,
    "fluoreto": 1.5,
}

# Faixa aceitável (mínimo, máximo)
RANGE_THRESHOLDS = {
    "ph": (6.0, 9.5),
}

PARAMETER_ALIASES = {
    "cloro_residual_livre_mg_l": "cloro_residual_livre",
    "cloro_residual_livre": "cloro_residual_livre",
    "turbidez_ut": "turbidez",
    "turbidez": "turbidez",
    "cor_uh": "cor",
    "cor": "cor",
    "ph": "ph",
    "coliformes_totais": "coliformes_totais",
    "escherichia_coli": "escherichia_coli",
    "fluoreto_mg_l": "fluoreto",
    "fluoreto": "fluoreto",
}


@dataclass
class SisaguaRecord:
    cod_mun: str
    municipio_alvo: str
    municipio_sisagua: str
    uf: str
    ano: int
    mes: int
    parametro: str
    parametro_original: str
    campo_slug: str
    campo_original: str
    classificacao: str
    valor: float
    dataset: str
    ponto_monitoramento: Optional[str]
    forma_abastecimento_tipo: Optional[str]
    forma_abastecimento_nome: Optional[str]
    forma_abastecimento_codigo: Optional[str]
    eta_uta_nome: Optional[str]
    instituicao_sigla: Optional[str]
    instituicao_nome: Optional[str]
    fonte_arquivo: str


def load_municipios(path: Path) -> Dict[str, str]:
    df = pd.read_csv(path, dtype={"ibge_code": "string"})
    df = df[df["is_rmb"] == 1]
    df["ibge_code"] = df["ibge_code"].str.zfill(7)
    mapping: Dict[str, str] = {}
    for code, name in zip(df["ibge_code"], df["name"]):
        mapping[code] = name
        mapping[code[:-1]] = name  # alguns conjuntos usam código IBGE com 6 dígitos
    return mapping


def iter_sisagua_sources(root: Path) -> Iterable[Path]:
    entries = set()
    for pattern in ("*.zip", "*.csv"):
        for path in root.glob(pattern):
            if path.name not in entries:
                entries.add(path.name)
    for name in sorted(entries):
        yield root / name


def to_ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def slugify(text: str) -> str:
    normalized = to_ascii(text)
    replacements = {
        ">=": " gte ",
        "<=": " lte ",
        "<": " lt ",
        ">": " gt ",
        "=": " eq ",
        "%": " pct ",
        "/": " ",
        "\\": " ",
        "-": " ",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    slug = re.sub(r"[^a-z0-9]+", "_", normalized.lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def normalize_parameter(name: str) -> str:
    slug = slugify(name)
    return PARAMETER_ALIASES.get(slug, slug)


def parse_float(raw: str) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    txt = str(raw).strip()
    if not txt:
        return None
    txt_lower = txt.lower()
    if txt_lower in {"na", "nan", "null", "none", "sem informacao"}:
        return None
    txt = txt.replace(".", "").replace(",", ".")
    try:
        value = float(txt)
    except ValueError:
        return None
    return value


def extract_numbers(text: str) -> List[float]:
    numbers = []
    for match in re.findall(r"\d+(?:[\.,]\d+)?", text):
        numbers.append(float(match.replace(".", "").replace(",", ".")))
    return numbers


def clean_ibge_code(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return None
    if len(digits) >= 7:
        return digits[:7]
    if len(digits) == 6:
        return digits
    return digits.zfill(6)


def classify_campo(parametro: str, campo: str) -> Optional[str]:
    campo_lower = campo.lower()
    campo_norm = to_ascii(campo_lower)

    if "amostras analisadas" in campo_norm:
        return "total"

    if parametro == "coliformes_totais":
        if "ausencia" in campo_norm:
            return "conforme"
        if "presenca" in campo_norm:
            return "nao_conforme"
        return None

    if parametro == "escherichia_coli":
        if "ausencia" in campo_norm:
            return "conforme"
        if "presenca" in campo_norm:
            return "nao_conforme"
        return None

    if parametro == "cloro_residual_livre":
        if any(token in campo_norm for token in ["> 5,0", ">5,0", "> 5.0", ">5.0"]):
            return "nao_conforme"
        if any(token in campo_norm for token in ["< 0,2", "<0,2", "< 0.2", "<0.2"]):
            return "nao_conforme"
        within_range_tokens = [
            ">= 0,2", ">=0,2", ">= 0.2", ">=0.2",
            ">= 2,0", ">=2,0", ">= 2.0", ">=2.0",
        ]
        if any(token in campo_norm for token in within_range_tokens) and (
            "<= 5,0" in campo_norm
            or "<=5,0" in campo_norm
            or "<= 5.0" in campo_norm
            or "<=5.0" in campo_norm
            or "<= 2,0" in campo_norm
            or "<=2,0" in campo_norm
            or "<= 2.0" in campo_norm
            or "<=2.0" in campo_norm
        ):
            return "conforme"
        return None

    if parametro in SINGLE_BOUND_THRESHOLDS:
        threshold = SINGLE_BOUND_THRESHOLDS[parametro]
        numbers = extract_numbers(campo_norm)
        has_le = "<=" in campo_norm or "≤" in campo_norm
        has_lt = "<" in campo_norm or "＜" in campo_norm
        has_gt = ">" in campo_norm or "＞" in campo_norm
        if has_le or has_lt:
            if numbers and max(numbers) <= threshold:
                return "conforme"
        if has_gt and not has_le and numbers:
            if min(numbers) > threshold:
                return "nao_conforme"
        return None

    if parametro in RANGE_THRESHOLDS:
        lower, upper = RANGE_THRESHOLDS[parametro]
        if all(token in campo_norm for token in [">=", "<="]):
            numbers = extract_numbers(campo_norm)
            if len(numbers) >= 2:
                low_value, high_value = numbers[0], numbers[1]
                if low_value >= lower and high_value <= upper:
                    return "conforme"
        if any(token in campo_norm for token in ["<", "<=", "lt", "lte"]):
            numbers = extract_numbers(campo_norm)
            if numbers and max(numbers) < lower:
                return "nao_conforme"
        if any(token in campo_norm for token in [">", ">=", "gt", "gte"]):
            numbers = extract_numbers(campo_norm)
            if numbers and min(numbers) > upper:
                return "nao_conforme"
        return None

    if "percentil 95" in campo_norm:
        return "percentil_95"

    return None


def process_source(
    source_path: Path,
    municipios: Dict[str, str],
) -> List[SisaguaRecord]:
    records: List[SisaguaRecord] = []
    dataset_name = (
        "demais_parametros" if "demais" in source_path.name else "parametros_basicos"
    )

    def iter_rows(handle: Iterable[Dict[str, str]]) -> None:
        nonlocal records
        for row in handle:
            uf = (row.get("UF") or "").strip()
            cod = clean_ibge_code(row.get("Código IBGE"))
            if uf != "PA" or cod not in municipios:
                continue

            valor = parse_float(row.get("Valor"))
            if valor is None:
                continue

            ano = row.get("Ano de referência")
            mes = row.get("Mês de referência")
            try:
                ano_int = int(float(str(ano).strip()))
                mes_int = int(float(str(mes).strip()))
            except (TypeError, ValueError):
                continue

            parametro_original = (row.get("Parâmetro") or "").strip()
            campo_original = (row.get("Campo") or "").strip()
            if not parametro_original or not campo_original:
                continue

            parametro = normalize_parameter(parametro_original)
            campo_slug = slugify(campo_original)
            classificacao = classify_campo(parametro, campo_original) or "nao_classificado"

            records.append(
                SisaguaRecord(
                    cod_mun=cod,
                    municipio_alvo=municipios[cod],
                    municipio_sisagua=(row.get("Município") or "").strip(),
                    uf=uf,
                    ano=ano_int,
                    mes=mes_int,
                    parametro=parametro,
                    parametro_original=parametro_original,
                    campo_slug=campo_slug,
                    campo_original=campo_original,
                    classificacao=classificacao,
                    valor=valor,
                    dataset=dataset_name,
                    ponto_monitoramento=(row.get("Ponto de Monitoramento") or "").strip() or None,
                    forma_abastecimento_tipo=(row.get("Tipo da Forma de Abastecimento") or "").strip() or None,
                    forma_abastecimento_nome=(row.get("Nome da Forma de Abastecimento") or "").strip() or None,
                    forma_abastecimento_codigo=(row.get("Código Forma de abastecimento") or "").strip() or None,
                    eta_uta_nome=(row.get("Nome da ETA / UTA") or "").strip() or None,
                    instituicao_sigla=(row.get("Sigla da Instituição") or "").strip() or None,
                    instituicao_nome=(row.get("Nome da Instituição") or "").strip() or None,
                    fonte_arquivo=source_path.name,
                )
            )

    if source_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(source_path) as zf:
            members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
            if not members:
                print(f"[WARN] Nenhum CSV encontrado em {source_path.name}", file=sys.stderr)
                return records
            for member in members:
                with zf.open(member) as raw:
                    # Força a decodificação para latin1, que é comum em dados do governo brasileiro
                    # e foi identificado como a codificação do arquivo de 2020.
                    reader = csv.DictReader(io.TextIOWrapper(raw, encoding="latin1"), delimiter=";")
                    iter_rows(reader)
    else:
        # Garante que arquivos CSV abertos diretamente também usem a codificação latin1.
        with source_path.open("r", encoding="latin1", errors="replace") as raw:
            reader = csv.DictReader(raw, delimiter=";")
            iter_rows(reader)

    return records


def aggregate_records(records: List[SisaguaRecord]) -> pd.DataFrame:
    df = pd.DataFrame([r.__dict__ for r in records])
    if df.empty:
        raise SystemExit("Nenhum registro SISAGUA encontrado para os municípios da RMB.")

    group_columns = [
        "cod_mun",
        "municipio_alvo",
        "municipio_sisagua",
        "uf",
        "ano",
        "mes",
        "parametro",
        "parametro_original",
        "dataset",
        "ponto_monitoramento",
        "forma_abastecimento_tipo",
        "forma_abastecimento_nome",
        "forma_abastecimento_codigo",
        "eta_uta_nome",
        "instituicao_sigla",
        "instituicao_nome",
        "fonte_arquivo",
    ]

    # CORREÇÃO: Preenche valores nulos em colunas de agrupamento para evitar que
    # o groupby descarte registros inteiros se uma chave for nula.
    # Isso é particularmente importante para colunas textuais opcionais.
    for col in group_columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("N/A")

    summary = (
        df.groupby(group_columns + ["classificacao"], dropna=False)["valor"]
        .sum()
        .reset_index()
    )

    # DEBUG: Verificar se 2020 sobreviveu ao groupby
    if 2020 in summary["ano"].unique():
        print("\\n[DEBUG AGG] O ano de 2020 sobreviveu à operação de groupby.")
    else:
        print("\\n[DEBUG AGG] FALHA: O ano de 2020 foi perdido durante o groupby.")

    pivot = summary.pivot_table(
        index=group_columns,
        columns="classificacao",
        values="valor",
        fill_value=0.0,
    )

    # DEBUG: Verificar se 2020 sobreviveu ao pivot
    if 2020 in pivot.reset_index()["ano"].unique():
        print("[DEBUG AGG] O ano de 2020 sobreviveu à operação de pivot.")
    else:
        print("[DEBUG AGG] FALHA: O ano de 2020 foi perdido durante o pivot.")

    pivot = pivot.reset_index()

    for col in ["total", "conforme", "nao_conforme", "percentil_95", "nao_classificado"]:
        if col not in pivot.columns:
            pivot[col] = 0.0

    pivot = pivot.rename(
        columns={
            "total": "amostras_total",
            "conforme": "amostras_conformes",
            "nao_conforme": "amostras_nao_conformes",
            "nao_classificado": "amostras_sem_classificacao",
            "percentil_95": "percentil_95",
        }
    )

    mask_sem_total = pivot["amostras_total"] <= 0
    pivot.loc[mask_sem_total, "amostras_total"] = (
        pivot.loc[mask_sem_total, ["amostras_conformes", "amostras_nao_conformes", "amostras_sem_classificacao"]]
        .sum(axis=1)
    )

    denom = pivot[["amostras_conformes", "amostras_nao_conformes"]].sum(axis=1)
    pivot["pct_conformes"] = pd.NA
    with pd.option_context("mode.use_inf_as_na", True):
        mask_valid = denom > 0
        pivot.loc[mask_valid, "pct_conformes"] = (
            pivot.loc[mask_valid, "amostras_conformes"] / denom[mask_valid] * 100
        )

    return pivot


def write_partitioned(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df)
    pq.write_to_dataset(
        table,
        root_path=str(out_dir),
        partition_cols=["ano", "mes"],
        existing_data_behavior="delete_matching",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Converte SISAGUA Bronze em Silver Parquet")
    parser.add_argument("--input-dir", default="data/bronze/sisagua", help="Diretório com os arquivos ZIP Bronze")
    parser.add_argument("--municipios", default="config/rmb_municipios.csv", help="CSV com os municípios-alvo")
    parser.add_argument("--output-dir", default="data/silver/sisagua", help="Diretório de saída para o Silver")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise SystemExit(f"Diretório não encontrado: {input_dir}")

    municipios = load_municipios(Path(args.municipios))
    if not municipios:
        raise SystemExit("CSV de municípios vazio ou sem flag is_rmb=1.")

    all_records: List[SisaguaRecord] = []
    for source in iter_sisagua_sources(input_dir):
        print(f"[SISAGUA] Processando {source.name} ...")
        records = process_source(source, municipios)
        print(f"  -> {len(records)} registros relevantes")
        all_records.extend(records)

    if not all_records:
        raise SystemExit("Nenhum registro SISAGUA processado. Verifique os filtros.")

    print("\\n[DEBUG] Anos encontrados nos registros brutos antes da agregação:")
    debug_df_raw = pd.DataFrame([r.__dict__ for r in all_records])
    if not debug_df_raw.empty:
        print(sorted(debug_df_raw["ano"].unique()))

    df = aggregate_records(all_records)

    print("\\n[DEBUG] Anos encontrados no DataFrame final antes da escrita:")
    if not df.empty:
        print(sorted(df["ano"].unique()))

    write_partitioned(df, Path(args.output_dir))
    print(
        f"[OK] SISAGUA Silver gerado: {len(df)} linhas agregadas em {args.output_dir} (particionado por ano/mes)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
