#!/usr/bin/env python3
"""Converte os CSVs de estações do INMET (Bronze) para Parquet particionado (Silver)."""

import argparse
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def slugify(text: str) -> str:
    """Cria um slug de um texto, removendo caracteres especiais e normalizando."""
    # Normaliza para remover acentos
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    # Remove caracteres não alfanuméricos, exceto espaços e underscores
    text = re.sub(r"[^a-z0-9_ ]", "", text)
    # Substitui espaços por underscores
    text = re.sub(r"\s+", "_", text).strip("_")
    return text

def get_column_mapping(header_row: pd.Series) -> dict[str, str]:
    """
    Cria um mapeamento de nomes de colunas originais para nomes padronizados.
    Esta versão é mais robusta para lidar com variações nos nomes das colunas.
    """
    import unicodedata
    mapping = {}
    
    # Mapeamentos conhecidos de variações de nome para nome padrão
    # A chave é uma tupla de possíveis nomes (em minúsculas e normalizados)
    known_mappings = {
        "data": ("data", "data (yyyy-mm-dd)"),
        "hora_utc": ("hora utc", "hora (utc)"),
        "chuva_mm": ("precipitacao total, horario (mm)", "precipitacao total horaria (mm)"),
        "pressao_atm_mb": ("pressao atmosferica ao nivel da estacao, horaria (mb)",),
        "radiacao_global_kj_m2": ("radiacao global (kj/m²)", "radiacao global"),
        "temp_c": ("temperatura do ar - bulbo seco, horaria (°c)", "temperatura do ar - bulbo seco, horaria (c)"),
        "umid_rel_pct": ("umidade relativa do ar, horaria (%)",),
        "vento_dir_graus": ("vento, direcao horaria (gr) (° (gr))", "vento, direcao horaria (gr)"),
        "vento_rajada_ms": ("vento, rajada maxima (m/s)",),
        "vento_vel_ms": ("vento, velocidade horaria (m/s)",),
    }

    # Inverte o dicionário para mapear cada variação ao seu nome padrão
    variation_to_standard_map = {}
    for standard_name, variations in known_mappings.items():
        for var in variations:
            variation_to_standard_map[var] = standard_name

    # Mapeia as colunas do arquivo para os nomes padronizados
    for col_original in header_row:
        if not col_original or pd.isna(col_original):
            continue
        
        # Normaliza o nome da coluna original para comparação (minúsculas, sem acentos)
        clean_col = unicodedata.normalize("NFKD", col_original).encode("ascii", "ignore").decode("ascii").lower().strip()

        if clean_col in variation_to_standard_map:
            mapping[col_original] = variation_to_standard_map[clean_col]
            
    return mapping

def process_inmet_csv(file_path: Path, station_code: str) -> pd.DataFrame | None:
    """Lê, limpa e padroniza um único arquivo CSV do INMET."""
    try:
        # Lê os dados, tratando valores nulos e diferentes formatos
        df = pd.read_csv(
            file_path,
            sep=";",
            encoding="latin1",
            skiprows=8,
            header=0, # A primeira linha após pular 8 é o cabeçalho
            decimal=",",
            na_values=["-9999", "-9999.0", ""],
            keep_default_na=True,
        )

        # Renomeia as colunas usando o mapeamento robusto
        df = df.rename(columns=get_column_mapping(df.columns))

        # Remove colunas totalmente vazias que podem surgir do parsing
        df = df.loc[:, ~df.columns.str.contains('^unnamed')]

        # Combina data e hora em um único campo de timestamp
        # Trata os dois formatos de hora encontrados ('00:00' e '0000 UTC')
        df["hora_utc"] = df["hora_utc"].astype(str).str.replace(" UTC", "").str.replace(":", "").str.zfill(4)
        
        # Trata os dois formatos de data ('YYYY-MM-DD' e 'YYYY/MM/DD')
        if "/" in df["data"].iloc[0]:
            dt_format = "%Y/%m/%d %H%M"
        else:
            dt_format = "%Y-%m-%d %H%M"
            
        df["timestamp_utc"] = pd.to_datetime(df["data"] + " " + df["hora_utc"], format=dt_format)
        
        # Adiciona metadados
        df["ano"] = df["timestamp_utc"].dt.year
        df["mes"] = df["timestamp_utc"].dt.month
        df["estacao"] = station_code

        # Seleciona e reordena colunas úteis
        final_cols = [
            "timestamp_utc", "ano", "mes", "estacao",
            "chuva_mm", "temp_c", "umid_rel_pct",
            "vento_vel_ms", "vento_dir_graus", "vento_rajada_ms",
            "pressao_atm_mb", "radiacao_global_kj_m2"
        ]
        
        # Garante que todas as colunas existam, preenchendo com NaN se não existirem
        for col in final_cols:
            if col not in df.columns:
                df[col] = pd.NA

        return df[final_cols]

    except Exception as e:
        print(f"Erro ao processar {file_path.name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Converte dados do INMET de CSV para Parquet particionado.")
    parser.add_argument("--input-dir", type=str, default="data/bronze/inmet", help="Diretório raiz com os dados brutos do INMET.")
    parser.add_argument("--output-dir", type=str, default="data/silver/inmet", help="Diretório de saída para os arquivos Parquet.")
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Lista apenas os arquivos .CSV nos subdiretórios diretos (ano)
    all_files = []
    for year_dir in sorted(input_path.iterdir()): # Adicionado sorted() para ordem cronológica
        if year_dir.is_dir():
            # Garante que estamos processando apenas os arquivos do Pará (PA)
            all_files.extend(year_dir.glob("INMET_N_PA_*.CSV"))

    if not all_files:
        raise SystemExit(f"Nenhum arquivo .CSV encontrado em {input_path}")

    all_data = []
    for file in all_files:
        print(f"Processando {file.name}...")
        # Extrai o código da estação do nome do arquivo (ex: A201)
        match = re.search(r"_(A\d{3})_", file.name)
        if not match:
            print(f"  -> Aviso: Não foi possível extrair o código da estação de {file.name}. Pulando.")
            continue
        
        station_code = match.group(1)
        df = process_inmet_csv(file, station_code)
        if df is not None:
            all_data.append(df)

    if not all_data:
        raise SystemExit("Nenhum dado do INMET foi processado com sucesso.")

    # Concatena todos os dataframes em um só
    final_df = pd.concat(all_data, ignore_index=True)

    # Converte colunas para tipos numéricos eficientes
    for col in ["chuva_mm", "temp_c", "umid_rel_pct", "vento_vel_ms", "vento_dir_graus", "vento_rajada_ms", "pressao_atm_mb", "radiacao_global_kj_m2"]:
        final_df[col] = pd.to_numeric(final_df[col], errors="coerce")

    # Escreve o dataset particionado
    table = pa.Table.from_pandas(final_df)
    pq.write_to_dataset(
        table,
        root_path=output_path,
        partition_cols=["estacao", "ano"],
        existing_data_behavior="delete_matching",
    )

    print(f"\\n[OK] Dados do INMET convertidos com sucesso para {output_path}")
    print(f"Total de registros processados: {len(final_df)}")
    print(f"Estações encontradas: {final_df['estacao'].unique().tolist()}")
    print(f"Anos processados: {sorted(final_df['ano'].unique().tolist())}")

if __name__ == "__main__":
    main()
