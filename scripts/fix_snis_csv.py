# scripts/fix_snis_csv.py
from pathlib import Path
import pandas as pd

IN = Path("data/gold/snis_rmb_indicadores.csv")
OUT_CSV = Path("data/gold/snis_rmb_indicadores_v2.csv")
OUT_PARQ = Path("data/gold/snis_rmb_indicadores_v2.parquet")

# 1) Carrega
df = pd.read_csv(IN)

# 2) Padroniza código IBGE (7 dígitos) com fallback pelo nome do município
IBGE_MAP = {
    "ANANINDEUA": "1500800",
    "BELÉM": "1501402",
    "BENEVIDES": "1501501",
    "MARITUBA": "1504422",
    "SANTA BÁRBARA DO PARÁ": "1506351",
    "SANTA IZABEL DO PARÁ": "1506500",
}
def norm_name(s: str) -> str:
    if not isinstance(s, str): return ""
    import unicodedata
    s2 = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode()
    return s2.upper().strip()

df["__mun_up"] = df["municipio"].map(norm_name)
def fix_cod(row):
    # tenta pelo nome (100% confiável)
    if row["__mun_up"] in IBGE_MAP:
        return IBGE_MAP[row["__mun_up"]]
    # se vier número, garante 7 dígitos
    raw = str(row.get("cod_mun","")).strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 6:
        return "0" + digits
    if len(digits) >= 7:
        return digits[:7]
    return digits or None

df["cod_mun"] = df.apply(fix_cod, axis=1)
df.drop(columns=["__mun_up"], inplace=True)

# 3) Corrige percentuais (se >100, divide por 100)
pct_cols = [
    "idx_atend_agua_total","idx_atend_agua_urbano",
    "idx_coleta_esgoto","idx_tratamento_esgoto","idx_esgoto_tratado_ref_agua",
    "idx_hidrometracao","idx_perdas_distribuicao"
]
for c in pct_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df.loc[df[c] > 100, c] = df.loc[df[c] > 100, c] / 100.0

# 4) Corrige grandezas físicas infladas (limiar simples)
for c in ["idx_perdas_lineares","idx_perdas_por_ligacao"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df.loc[df[c] > 1000, c] = df.loc[df[c] > 1000, c] / 100.0

# 5) Ordena colunas e salva v2
ordem = ["cod_mun","municipio","ano"] + [c for c in df.columns if c not in ["cod_mun","municipio","ano"]]
df = df[ordem].sort_values(["municipio","ano"])
df.to_csv(OUT_CSV, index=False)
try:
    df.to_parquet(OUT_PARQ, index=False)
except Exception:
    pass

# 6) Mostra um resumo rápido para você validar
def resumo_min_max(cols):
    out = []
    for c in cols:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            out.append((c, float(s.min()) if s.notna().any() else None, float(s.max()) if s.notna().any() else None))
    return out

print("\nResumo (faixas após correção):")
for c, mn, mx in resumo_min_max(pct_cols + ["idx_perdas_lineares","idx_perdas_por_ligacao"]):
    print(f" - {c:28s} min={mn}  max={mx}")

print("\nArquivos corrigidos:")
print(" -", OUT_CSV)
print(" -", OUT_PARQ)
