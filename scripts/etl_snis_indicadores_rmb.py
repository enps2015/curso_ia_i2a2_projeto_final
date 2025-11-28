"""ETL dos indicadores do SNIS/SINISA para a RMB (2018-2023).

Atualiza as referências de caminhos conforme a árvore em ``data/bronze/snis``.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

BASE_SNIS = Path("data/bronze/snis")

PLANILHAS_POR_ANO: Dict[int, List[Path]] = {
    2018: [
        BASE_SNIS / "Planilhas_AE2018_Completa" / "Planilha_LEP_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2018_Completa" / "Planilha_LPR_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2018_Completa" / "Planilha_LPU_Indicadores.xls",
    ],
    2019: [
        BASE_SNIS / "Planilhas_AE2019_Completa" / "Planilha_LEP_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2019_Completa" / "Planilha_LPR_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2019_Completa" / "Planilha_LPU_Indicadores.xls",
    ],
    2020: [
        BASE_SNIS / "Planilhas_AE2020_Completa" / "Planilha_LEP_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2020_Completa" / "Planilha_LPR_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2020_Completa" / "Planilha_LPU_Indicadores.xls",
    ],
    2021: [
        BASE_SNIS / "Planilhas_AE2021_Completa" / "Planilha_LEP_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2021_Completa" / "Planilha_LPR_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2021_Completa" / "Planilha_LPU_Indicadores.xls",
    ],
    2022: [
        BASE_SNIS / "Planilhas_AE2022_Completa" / "Planilha_LEP_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2022_Completa" / "Planilha_LPR_Indicadores.xls",
        BASE_SNIS / "Planilhas_AE2022_Completa" / "Planilha_LPU_Indicadores.xls",
    ],
    2023: [
        BASE_SNIS
        / "SINISA_AGUA_Planilhas_2023_v2.1.1"
        / "Água - Base Municipal"
        / "SINISA_AGUA_Indicadores_Base Municipal_2023_V2.xlsx",
        BASE_SNIS
        / "SINISA_ESGOTO_Planilhas_2023_v2"
        / "Esgoto - Base Municipal"
        / "SINISA_ESGOTO_Indicadores_Base Municipal_2023_V2.xlsx",
    ],
}

OUT_DIR = Path("data/gold")

RMB_MUNS = {
    "BELÉM",
    "ANANINDEUA",
    "MARITUBA",
    "BENEVIDES",
    "SANTA BÁRBARA DO PARÁ",
    "SANTA IZABEL DO PARÁ",
}


def fix_str(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    try:
        text = text.encode("latin1").decode("utf-8")
    except Exception:
        pass
    return text.strip()


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def sanitize_label(label: str) -> str:
    label = strip_accents(label.lower())
    return re.sub(r"[^a-z0-9]+", "_", label).strip("_")


def strip_upper(text: str) -> str:
    return strip_accents(text).upper()


def to_float_br(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value)
    text = re.sub(r"[^0-9,.-]+", "", text).strip()
    if not text or text in {"-", "."}:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def find_header_row(raw: pd.DataFrame) -> int | None:
    for idx in range(min(30, len(raw))):
        row = raw.iloc[idx].fillna("").map(lambda x: sanitize_label(fix_str(x)))
        if any("municipio" in cell for cell in row) and any(
            key in row.tolist() for key in ["codigo_do_municipio", "codigo_ibge", "cod_ibge"]
        ):
            return idx
    return None


def find_code_row(raw: pd.DataFrame, header_idx: int) -> int | None:
    pattern = re.compile(r"(in|ia[g|e])[0-9]{3}")
    for idx in range(header_idx + 1, min(header_idx + 6, len(raw))):
        row = raw.iloc[idx].fillna("").map(lambda x: sanitize_label(fix_str(x)))
        if any(pattern.search(cell) for cell in row):
            return idx
    return None


def build_columns(raw: pd.DataFrame, header_idx: int, code_idx: int | None) -> List[str]:
    header = raw.iloc[header_idx].fillna("").map(fix_str)
    codes = (
        raw.iloc[code_idx].fillna("").map(fix_str)
        if code_idx is not None
        else [""] * len(header)
    )
    columns: List[str] = []
    seen: Dict[str, int] = {}
    for pos, (label, code) in enumerate(zip(header, codes)):
        label = label.replace("\n", " ").strip(" -")
        code = code.replace("\n", " ").strip(" -")
        chosen = label or code or f"col_{pos}"
        key = sanitize_label(chosen)
        if key in seen:
            seen[key] += 1
            chosen = f"{chosen}_{seen[key]}"
        else:
            seen[key] = 0
        columns.append(chosen)
    return columns


def read_excel_normalized(path: Path) -> Iterable[pd.DataFrame]:
    try:
        workbook = pd.ExcelFile(path)
    except Exception:
        return []

    tables: List[pd.DataFrame] = []
    for sheet in workbook.sheet_names:
        try:
            raw = workbook.parse(sheet, header=None, dtype=str)
        except Exception:
            continue
        header_idx = find_header_row(raw)
        if header_idx is None:
            continue
        code_idx = find_code_row(raw, header_idx)
        start_idx = (code_idx if code_idx is not None else header_idx) + 1
        columns = build_columns(raw, header_idx, code_idx)
        data = raw.iloc[start_idx:].copy()
        data.columns = columns
        data = data.dropna(how="all")
        if data.empty:
            continue
        for col in data.columns:
            if data[col].dtype == object:
                data[col] = data[col].map(lambda x: fix_str(x) if isinstance(x, str) else x)
        tables.append(data)
    return tables


COL_ALIASES: Dict[str, Tuple[str, ...]] = {
    "cod_mun": (
        "codigo_do_municipio",
        "codigo_municipio",
        "codigo_ibge",
        "cod_ibge",
        "codigo_do_ibge",
    ),
    "municipio": ("municipio",),
    "uf": ("uf", "sigla_da_uf"),
}

IND_PAT: Dict[str, Tuple[str, ...]] = {
    "idx_atend_agua_total": (
        "indice_de_atendimento_total_de_agua",
        "atendimento_da_populacao_total_com_rede_de_abastecimento_de_agua",
    ),
    "idx_atend_agua_urbano": (
        "indice_de_atendimento_urbano_de_agua",
        "atendimento_da_populacao_urbana_com_rede_de_abastecimento_de_agua",
    ),
    "idx_coleta_esgoto": (
        "indice_de_coleta_de_esgoto",
        "atendimento_da_populacao_total_com_rede_coletora_de_esgotos",
    ),
    "idx_tratamento_esgoto": (
        "indice_de_tratamento_de_esgoto",
        "tratamento_do_volume_total_de_esgoto_coletado",
    ),
    "idx_esgoto_tratado_ref_agua": (
        "indice_de_esgoto_tratado_referido_a_agua_consumida",
    ),
    "idx_hidrometracao": (
        "indice_de_hidrometracao",
    ),
    "idx_perdas_distribuicao": (
        "indice_de_perdas_na_distribuicao",
    ),
    "idx_perdas_lineares": (
        "indice_bruto_de_perdas_lineares",
    ),
    "idx_perdas_por_ligacao": (
        "indice_de_perdas_por_ligacao",
    ),
    "tarifa_media_praticada": (
        "tarifa_media_praticada",
    ),
    "tarifa_media_agua": (
        "tarifa_media_de_agua",
    ),
    "tarifa_media_esgoto": (
        "tarifa_media_de_esgoto",
    ),
    "despesa_total_m3": (
        "despesa_total_com_os_servicos_por_m3_faturado",
        "despesa_total_por_m3",
    ),
    "despesa_exploracao_m3": (
        "despesa_de_exploracao_por_m3_faturado",
    ),
}

RMB_MUNS_SAN = {strip_upper(name) for name in RMB_MUNS}


def locate_column(normalized_map: Dict[str, str], aliases: Tuple[str, ...]) -> str | None:
    for alias in aliases:
        for column, normalized in normalized_map.items():
            if normalized == alias:
                return column
    return None


def extract_indicators(table: pd.DataFrame) -> pd.DataFrame:
    if table.empty:
        return pd.DataFrame()

    normalized_map = {col: sanitize_label(col) for col in table.columns}

    code_col = locate_column(normalized_map, COL_ALIASES["cod_mun"])
    name_col = locate_column(normalized_map, COL_ALIASES["municipio"])
    uf_col = locate_column(normalized_map, COL_ALIASES["uf"])

    if code_col is None or name_col is None:
        return pd.DataFrame()

    frame = table.copy()
    for col in [code_col, name_col, uf_col]:
        if col and frame[col].dtype == object:
            frame[col] = frame[col].map(lambda x: fix_str(x) if isinstance(x, str) else x)

    if uf_col:
        frame = frame[frame[uf_col].map(lambda x: strip_upper(str(x)) == "PA")]
    frame["__mun_norm"] = frame[name_col].map(lambda x: strip_upper(str(x)))
    frame = frame[frame["__mun_norm"].isin(RMB_MUNS_SAN)]
    if frame.empty:
        return pd.DataFrame()

    cod_series = (
        frame[code_col]
        .astype(str)
        .str.extract(r"(\d{6,7})", expand=False)
        .str.strip()
    )

    dataset = pd.DataFrame({
        "cod_mun": cod_series,
        "municipio": frame[name_col],
    })

    dataset = dataset.dropna(subset=["cod_mun"])

    for target, patterns in IND_PAT.items():
        match = next(
            (
                column
                for column, normalized in normalized_map.items()
                if normalized in patterns or any(pattern in normalized for pattern in patterns)
            ),
            None,
        )
        if match:
            dataset[target] = frame[match].map(to_float_br)

    dataset = dataset.groupby(["cod_mun", "municipio"], as_index=False).max(numeric_only=True)
    return dataset


def choose_one_prestador(frames: List[pd.DataFrame]) -> pd.DataFrame:
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    base = pd.concat(frames, ignore_index=True)
    score_cols = [
        col
        for col in ["idx_atend_agua_total", "idx_coleta_esgoto", "idx_tratamento_esgoto"]
        if col in base.columns
    ]
    if score_cols:
        score = base[score_cols].fillna(0).sum(axis=1)
    else:
        score = pd.Series(0, index=base.index)
    base = base.assign(_score=score)
    base = base.sort_values(["municipio", "_score"], ascending=[True, False])
    base = base.drop_duplicates(subset=["cod_mun"], keep="first")
    return base.drop(columns="_score", errors="ignore")


def collect_year(year: int, paths: Iterable[Path]) -> Tuple[List[pd.DataFrame], pd.DataFrame]:
    raw_frames: List[pd.DataFrame] = []
    for path in paths:
        if not path.exists():
            continue
        for table in read_excel_normalized(path):
            extracted = extract_indicators(table)
            if extracted.empty:
                continue
            enriched = extracted.assign(fonte_planilha=path.stem, ano=year)
            raw_frames.append(enriched)
    curated = choose_one_prestador(raw_frames)
    if not curated.empty:
        curated = curated.assign(ano=year)
    return raw_frames, curated


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_parts: List[pd.DataFrame] = []
    curated_parts: List[pd.DataFrame] = []

    for ano, arquivos in PLANILHAS_POR_ANO.items():
        ano_raw, ano_curated = collect_year(ano, arquivos)
        raw_parts.extend(ano_raw)
        if not ano_curated.empty:
            curated_parts.append(ano_curated)

    if raw_parts:
        raw = pd.concat(raw_parts, ignore_index=True)
        raw.to_csv(OUT_DIR / "snis_rmb_indicadores_raw.csv", index=False)

    if curated_parts:
        curated = pd.concat(curated_parts, ignore_index=True)
        curated.to_csv(OUT_DIR / "snis_rmb_indicadores.csv", index=False)
        try:
            curated.to_parquet(OUT_DIR / "snis_rmb_indicadores.parquet", index=False)
        except Exception:
            pass

    print("ETL concluído para", sorted(PLANILHAS_POR_ANO))


if __name__ == "__main__":
    main()


