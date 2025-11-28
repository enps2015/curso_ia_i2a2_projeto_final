#!/usr/bin/env python3
"""
Baixa os principais conjuntos SISAGUA (Controle Mensal – Parâmetros Básicos e Demais Parâmetros).
Uso:
  python scripts/sisagua_download.py --out data/sisagua
"""

import argparse
import os
import subprocess
import sys

DATASETS = [
    "sisagua-controle-mensal-parametros-basicos",
    "sisagua-controle-mensal-demais-parametros",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Diretório de saída")
    parser.add_argument("--base", default="https://opendatasus.saude.gov.br", help="Base CKAN")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    here = os.path.dirname(os.path.abspath(__file__))
    ckan = os.path.join(here, "ckan_fetch_dataset.py")
    for slug in DATASETS:
        print(f"[SISAGUA] Baixando {slug} ...")
        subprocess.check_call([sys.executable, ckan, "--base", args.base, "--slug", slug, "--out", args.out])
    print("[OK] SISAGUA concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
