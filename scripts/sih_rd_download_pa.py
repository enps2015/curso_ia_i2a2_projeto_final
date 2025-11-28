#!/usr/bin/env python3
"""
Baixa arquivos mensais SIH/RD (AIH reduzida) para o estado do Pará (PA) via FTP DATASUS.

Exemplo:
    python scripts/sih_rd_download_pa.py --out data/bronze/sih --year-start 2015 --year-end 2025
"""

import argparse
import os
import urllib.error
import urllib.request

from tqdm import tqdm

BASES = [
    "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/199201_200712/Dados/",
    "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/",
]
UF = "PA"


def filename_for(year: int, month: int) -> str:
    yy = str(year)[-2:]
    mm = f"{month:02d}"
    return f"RD{UF}{yy}{mm}.dbc"


def try_download(url: str, dest: str) -> bool:
    try:
        with urllib.request.urlopen(url) as response:
            total = int(response.headers.get("Content-Length", 0))
            with open(dest, "wb") as handle, tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc=os.path.basename(dest),
            ) as bar:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    handle.write(chunk)
                    bar.update(len(chunk))
        return True
    except urllib.error.HTTPError:
        return False
    except Exception as exc:
        print(f"[WARN] Falha em {url}: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    for year in range(args.year_start, args.year_end + 1):
        for month in range(1, 13):
            fname = filename_for(year, month)
            dest = os.path.join(args.out, fname)
            if os.path.exists(dest):
                continue
            ok = False
            for base in BASES:
                url = base + fname
                if try_download(url, dest):
                    ok = True
                    break
            if not ok:
                print(f"[MISS] Não encontrado: {fname}")
    print("[OK] SIH baixado (o que houve disponível).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
