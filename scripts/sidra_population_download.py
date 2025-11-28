#!/usr/bin/env python3
"""Baixa população municipal (SIDRA tabela 6579) para a RMB, gerando um CSV por ano."""

import argparse
import csv
import os
import re
from typing import Iterable

import requests

RMB_CODES = [1501402, 1500800, 1504422, 1501501, 1506351, 1506500, 1502400, 1501303]
VARIABLE_CODE = "9324"  # População residente estimada
SIDRA_BASE = "https://apisidra.ibge.gov.br/values/t/6579/n6/{codes}/v/{variable}/p/{period}"


def build_code_string(codes: Iterable[int]) -> str:
    return ",".join(str(code) for code in codes)


def dump_csv(data: list[dict], output_path: str) -> bool:
    fieldnames = [
        "municipio_codigo",
        "municipio_nome",
        "ano",
        "variavel_codigo",
        "variavel_nome",
        "unidade_codigo",
        "unidade_nome",
        "valor",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        if len(data) <= 1:
            return False

        rows = []
        for entry in data[1:]:
            rows.append(
                {
                    "municipio_codigo": entry.get("D1C"),
                    "municipio_nome": entry.get("D1N"),
                    "ano": entry.get("D3C"),
                    "variavel_codigo": entry.get("D2C"),
                    "variavel_nome": entry.get("D2N"),
                    "unidade_codigo": entry.get("MC"),
                    "unidade_nome": entry.get("MN"),
                    "valor": entry.get("V"),
                }
            )
        writer.writerows(rows)
        return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Diretório de saída")
    parser.add_argument("--years", required=True, help="Faixa de anos, ex.: 2001-2025")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    match = re.match(r"^(\d{4})-(\d{4})$", args.years)
    if not match:
        raise SystemExit("Parâmetro --years inválido. Use ex.: 2001-2025")
    start_year, end_year = map(int, match.groups())

    code_str = build_code_string(RMB_CODES)
    for year in range(start_year, end_year + 1):
        url = SIDRA_BASE.format(codes=code_str, variable=VARIABLE_CODE, period=year)
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        output_path = os.path.join(args.out, f"sidra6579_pop_{year}.csv")
        has_data = dump_csv(response.json(), output_path)
        if not has_data:
            print(f"[WARN] Sem registros publicados para {year}.")
    print("[OK] População baixada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
