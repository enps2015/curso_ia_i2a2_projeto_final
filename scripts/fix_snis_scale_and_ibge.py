# fix_snis_scale_and_ibge.py
from pathlib import Path
import pandas as pd

IN = Path("data/gold/snis_rmb_indicadores.csv")
OUT_CSV = Path("data/gold/snis_rmb_indicadores_v2.csv")
OUT_PARQ = Path("data/gold/snis_rmb_indicadores_v2.parquet")

df = pd.read_csv(IN)

# 1) padroniza IBGE para 7 dígitos (com fallback por nome)
IBGE_MAP = {
    "ANANINDEUA": "1500800",
    "BELÉM": "1501402",
    "BENEVIDES": "1501501",
    "MARITUBA": "1504422",
    "SANTA BÁRBARA DO PARÁ": "1506351",
    "SANTA IZABEL DO PARÁ": "1506500",
}
df["municipio_up"] = df["municipio"].str.normalize("NFKD").str.encode("ascii","ignore").str.decode().str.upper()
df["cod_mun"] = df.apply(
    lambda r: IBGE_MAP.get(r["municipio_up"], str(r["cod_mun"]).zfill(7)),
    axis=1
)
df.drop(columns=["municipio_up"], inplace=True)

# 2) corrige percentuais (>100 => divide por 100)
pct_cols = [
    "idx_atend_agua_total","idx_atend_agua_urbano","idx_coleta_esgoto",
    "idx_tratamento_esgoto","idx_esgoto_tratado_ref_agua",
    "idx_hidrometracao","idx_perdas_distribuicao"
]
for c in pct_cols:
    if c in df.columns:
        df[c] = df[c].where((df[c].isna()) | (df[c] <= 100), df[c] / 100.0)

# 3) corrige grandezas físicas com ponto de milhar (valor muito alto => divide por 100)
if "idx_perdas_lineares" in df.columns:
    df["idx_perdas_lineares"] = df["idx_perdas_lineares"].where(
        (df["idx_perdas_lineares"].isna()) | (df["idx_perdas_lineares"] <= 1000),
        df["idx_perdas_lineares"] / 100.0
    )

if "idx_perdas_por_ligacao" in df.columns:
    df["idx_perdas_por_ligacao"] = df["idx_perdas_por_ligacao"].where(
        (df["idx_perdas_por_ligacao"].isna()) | (df["idx_perdas_por_ligacao"] <= 1000),
        df["idx_perdas_por_ligacao"] / 100.0
    )

# ordena e salva
ordem = ["cod_mun","municipio","ano"] + [c for c in df.columns if c not in ["cod_mun","municipio","ano"]]
df = df[ordem].sort_values(["municipio","ano"])
df.to_csv(OUT_CSV, index=False)
try:
    df.to_parquet(OUT_PARQ, index=False)
except Exception:
    pass

print("SNIS (v2) salvo em:", OUT_CSV, OUT_PARQ)
