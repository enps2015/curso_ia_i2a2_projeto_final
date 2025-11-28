# scripts/siops_fetch.py
import argparse, os, time, sys
from urllib.parse import urljoin
import unicodedata

import pandas as pd
import requests
from tqdm import tqdm

BASE = "https://siops-consulta-publica-api.saude.gov.br/"
API_PREFIX = "v1"


def api_path(*segments) -> str:
    parts = [API_PREFIX.strip("/")]
    parts.extend(str(seg).strip("/") for seg in segments)
    return "/".join(parts)

# --- util: chamada segura com backoff ---
def get_json(path, params=None, sleep=0.5, allow_not_found=False):
    url = urljoin(BASE, path)
    for i in range(5):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                # Alguns endpoints podem devolver texto; tenta novamente
                time.sleep(sleep); continue
        if allow_not_found and r.status_code == 404:
            return []
        time.sleep(sleep * (i+1))
    raise RuntimeError(f"Falha GET {url} {params} -> {r.status_code} {r.text[:200]}")

# --- lista de municípios da RMB (8, incluindo Barcarena) ---
RMB8 = {
    "BELÉM",
    "ANANINDEUA",
    "MARITUBA",
    "BENEVIDES",
    "SANTA BÁRBARA DO PARÁ",
    "SANTA ISABEL DO PARÁ",
    "CASTANHAL",
    "BARCARENA",
}


def normalize_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name or "")
    return (
        normalized.encode("ascii", "ignore").decode("ascii").upper()
        if normalized
        else ""
    )


RMB8_NORMALIZED = {normalize_name(name) for name in RMB8}

def fetch_municipios_pa():
    # conforme metadados: endpoint 'v1/ente/municipal/{estado}'
    js = get_json(api_path("ente", "municipal", "15"))
    df = pd.DataFrame(js)
    # normaliza maiúsculas sem acento para bater com nosso set
    df["no_municipio_norm"] = df["no_municipio"].apply(normalize_name)
    rmb = df[df["no_municipio_norm"].isin(RMB8_NORMALIZED)].copy()
    rmb = rmb.rename(columns={"co_municipio":"cod_mun", "no_municipio":"municipio"})
    rmb = rmb[["cod_mun","municipio"]]
    if rmb.empty:
        raise RuntimeError("Não encontrei municípios da RMB via API. Verifique endpoint e nomes.")
    return rmb

def fetch_indicadores_municipais(cod_mun, ano, periodo, indicadores):
    # endpoint 'v1/indicador/municipal/{municipio}/{ano}/{periodo}'
    rows = []
    path = api_path("indicador", "municipal", cod_mun, ano, periodo)
    js = get_json(path, allow_not_found=True)
    df = pd.DataFrame(js)
    if df.empty:
        return rows
    # filtra apenas os indicadores desejados (numero_indicador como string float ex: '2.1')
    df = df[df["numero_indicador"].astype(str).isin([str(i) for i in indicadores])]
    for _,r in df.iterrows():
        rows.append({
            "cod_mun": cod_mun,
            "ano": ano,
            "periodo": periodo,
            "numero_indicador": str(r["numero_indicador"]),
            "ds_indicador": r["ds_indicador"],
            "numerador": r.get("numerador"),
            "denominador": r.get("denominador"),
            "valor": r.get("indicador_calculado"),
        })
    return rows

def fetch_subfuncao(cod_mun, ano, periodo):
    # endpoint 'v1/despesas-por-subfuncao/{uf}/{municipio}/{ano}/{periodo}' (vide metadados)
    path = api_path("despesas-por-subfuncao", "15", cod_mun, ano, periodo)
    js = get_json(path, allow_not_found=True)
    df = pd.DataFrame(js)
    if df.empty:
        return []
    df["cod_mun"] = cod_mun
    df["ano"] = ano
    df["periodo"] = periodo
    # mantém colunas-chaves e valores (valor1..valor10 variam por ano – manter todas)
    keep = ["cod_mun","ano","periodo","quadro","grupo","ordem","descricao",
            "valor1","valor2","valor3","valor4","valor5","valor6","valor7","valor8","valor9","valor10"]
    for c in keep:
        if c not in df.columns:
            df[c] = None
    return df[keep].to_dict(orient="records")

def main(outdir, ano_ini, ano_fim, anual=True, coletar_subfuncao=True):
    periodo = 2 if anual else 14  # padrão: anual
    indicadores = ["1.3","1.6","2.1","2.2","2.3","2.4","2.5","2.6","3.1","3.2"]

    rmb = fetch_municipios_pa()
    print("Municípios RMB via API:")
    print(rmb.to_string(index=False))

    ind_rows, sub_rows = [], []
    anos = list(range(ano_ini, ano_fim+1))
    for _, m in rmb.iterrows():
        for ano in tqdm(anos, desc=f"{m['municipio']}"):
            ind_rows += fetch_indicadores_municipais(m["cod_mun"], ano, periodo, indicadores)
            if coletar_subfuncao:
                sub_rows += fetch_subfuncao(m["cod_mun"], ano, periodo)
            time.sleep(0.25)  # politeness

    ind = pd.DataFrame(ind_rows)
    sub = pd.DataFrame(sub_rows)

    outdir = outdir.rstrip("/")
    os.makedirs(outdir, exist_ok=True)
    ind.to_csv(f"{outdir}/siops_indicadores_rmb_{ano_ini}_{ano_fim}.csv", index=False)
    if coletar_subfuncao:
        sub.to_csv(f"{outdir}/siops_subfuncao_rmb_{ano_ini}_{ano_fim}.csv", index=False)
    print("Pronto.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/bronze/siops", help="pasta de saída")
    ap.add_argument("--year-start", type=int, default=2018)
    ap.add_argument("--year-end", type=int, default=2025)
    ap.add_argument("--periodo-anual", action="store_true", default=True)
    ap.add_argument("--sem-subfuncao", action="store_true")
    args = ap.parse_args()
    main(args.out, args.year_start, args.year_end, anual=args.periodo_anual, coletar_subfuncao=not args.sem_subfuncao)
