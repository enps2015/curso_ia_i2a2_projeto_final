#!/usr/bin/env python3
"""
Converte os dados de população do IBGE (Bronze) para Parquet (Silver).

Lê múltiplos arquivos CSV do diretório de entrada, cada um contendo
estimativas de população para um ano específico. Consolida todos os anos
em um único DataFrame, seleciona e renomeia as colunas relevantes,
converte os tipos de dados e salva o resultado como um único arquivo Parquet.
"""

import argparse
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def process_population_data(input_dir: Path, output_path: Path):
    """
    Processa os arquivos CSV de população e os salva em formato Parquet.

    Args:
        input_dir: Diretório contendo os arquivos CSV brutos.
        output_path: Caminho para salvar o arquivo Parquet de saída.
    """
    all_files = list(input_dir.glob("sidra6579_pop_*.csv"))
    if not all_files:
        raise SystemExit(f"Nenhum arquivo CSV de população encontrado em {input_dir}")

    all_data = []
    for file in sorted(all_files):
        print(f"Processando {file.name}...")
        try:
            # Pula arquivos vazios ou que contêm apenas cabeçalho
            df = pd.read_csv(file)
            if df.empty:
                print(f"  -> Aviso: Arquivo '{file.name}' está vazio. Pulando.")
                continue
            all_data.append(df)
        except pd.errors.EmptyDataError:
            print(f"  -> Aviso: Arquivo '{file.name}' está vazio ou mal formatado. Pulando.")
            continue

    if not all_data:
        raise SystemExit("Nenhum dado de população válido foi encontrado para processar.")

    # Concatena todos os dataframes
    final_df = pd.concat(all_data, ignore_index=True)

    # Seleciona e renomeia as colunas de interesse
    final_df = final_df[["municipio_codigo", "ano", "valor"]]
    final_df = final_df.rename(columns={
        "municipio_codigo": "cod_mun",
        "ano": "ano",
        "valor": "populacao"
    })

    # Converte os tipos de dados para otimização
    final_df = final_df.astype({
        "cod_mun": "int32",
        "ano": "int32",
        "populacao": "int32"
    })

    # Garante que o diretório de saída exista
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Escreve o arquivo Parquet
    table = pa.Table.from_pandas(final_df)
    pq.write_table(table, output_path)

    print(f"\n[OK] Dados de população convertidos com sucesso para {output_path}")
    print(f"Total de registros processados: {len(final_df)}")
    print(f"Anos processados: {sorted(final_df['ano'].unique().tolist())}")


def main():
    parser = argparse.ArgumentParser(description="Converte dados de população do IBGE de CSV para Parquet.")
    parser.add_argument("--input-dir", type=str, default="data/bronze/ibge", help="Diretório raiz com os dados brutos de população.")
    parser.add_argument("--output-file", type=str, default="data/silver/ibge_populacao/populacao.parquet", help="Arquivo Parquet de saída.")
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    output_file_path = Path(args.output_file)

    process_population_data(input_path, output_file_path)


if __name__ == "__main__":
    main()
