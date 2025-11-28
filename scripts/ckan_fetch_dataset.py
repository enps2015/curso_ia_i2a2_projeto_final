#!/usr/bin/env python3
"""
Baixa todos os recursos (CSV/ZIP/JSON/XML) de um dataset CKAN (ex.: OPENDATASUS).
Uso:
  python ckan_fetch_dataset.py --base https://opendatasus.saude.gov.br --slug sisagua-controle-mensal-demais-parametros --out data/sisagua
"""

import argparse
import os
from urllib.parse import urljoin

import requests
from tqdm import tqdm


def list_resources(base_url: str, dataset_slug: str):
    api = urljoin(base_url, f"/api/3/action/package_show?id={dataset_slug}")
    response = requests.get(api, timeout=60)
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise RuntimeError(f"CKAN error: {data}")
    return data["result"]["resources"]


def download(url: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    local = os.path.join(out_dir, url.split("/")[-1].split("?")[0])
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        with open(local, "wb") as output, tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            desc=os.path.basename(local),
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    output.write(chunk)
                    bar.update(len(chunk))
    return local


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="https://opendatasus.saude.gov.br", help="Base CKAN (ex.: https://opendatasus.saude.gov.br)")
    parser.add_argument("--slug", required=True, help="Slug do dataset (ex.: sisagua-controle-mensal-demais-parametros)")
    parser.add_argument("--out", required=True, help="Diretório de saída")
    parser.add_argument("--formats", default="CSV,ZIP,JSON,XML", help="Formatos de recursos para baixar (separados por vírgula)")
    args = parser.parse_args()

    allowed = {item.strip().upper() for item in args.formats.split(",")}
    resources = list_resources(args.base, args.slug)

    downloaded = []
    for resource in resources:
        fmt = (resource.get("format") or "").upper()
        url = resource.get("url")
        if fmt in allowed and url:
            local = download(url, args.out)
            downloaded.append(local)
    print("Arquivos baixados:", *downloaded, sep="\n- ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
