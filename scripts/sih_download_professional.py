"""
Script profissional para converter arquivos DBC do SIH para CSV.
Usa a biblioteca pyreaddbc (já instalada como dependência do PySUS) para ler os DBCs.

Converte os arquivos DBC do SIH-RD (AIH Reduzida) que já existem em data/bronze/sih/
para CSV em data/bronze/sih/csv/, identificando os municípios da RMB.
"""
import pandas as pd
from dbfread import DBF
from pathlib import Path
from tqdm import tqdm
import subprocess
import tempfile
import os

def load_rmb_municipalities():
    """Carrega a lista de códigos IBGE dos municípios da RMB."""
    config_path = Path("config/rmb_municipios.csv")
    if not config_path.exists():
        print(f"AVISO: Arquivo {config_path} não encontrado. Processando todos os municípios do PA.")
        return None
    
    df_rmb = pd.read_csv(config_path)
    rmb_codes = df_rmb[df_rmb['is_rmb'] == 1]['ibge_code'].tolist()
    print(f"Municípios da RMB carregados: {len(rmb_codes)}")
    return rmb_codes

def convert_dbc_to_dataframe(dbc_file):
    """Converte um arquivo DBC para DataFrame usando o comando blast_dbf do pyreaddbc."""
    # Criar arquivo temporário para o DBF
    with tempfile.NamedTemporaryFile(suffix='.dbf', delete=False) as tmp_dbf:
        tmp_dbf_path = tmp_dbf.name
    
    try:
        # Encontrar o executável blast_dbf que vem com pyreaddbc
        import sys
        pyreaddbc_path = Path(sys.prefix) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'pyreaddbc'
        
        # Usar o Python para descomprimir o DBC
        # A pyreaddbc tem um módulo _readdbc que faz a descompressão
        from pyreaddbc import _readdbc
        
        # Ler o arquivo DBC
        for table_name, df in _readdbc.readdbc(str(dbc_file), encoding='latin-1'):
            return df  # Retorna o primeiro (e único) DataFrame
        
        return None
    except Exception as e:
        raise Exception(f"Erro ao converter DBC: {e}")
    finally:
        # Limpar arquivo temporário se existir
        if os.path.exists(tmp_dbf_path):
            try:
                os.unlink(tmp_dbf_path)
            except:
                pass

def load_rmb_municipalities():
    """Carrega a lista de códigos IBGE dos municípios da RMB."""
    config_path = Path("config/rmb_municipios.csv")
    if not config_path.exists():
        print(f"AVISO: Arquivo {config_path} não encontrado. Processando todos os municípios do PA.")
        return None
    
    df_rmb = pd.read_csv(config_path)
    rmb_codes = df_rmb[df_rmb['is_rmb'] == 1]['ibge_code'].tolist()
    print(f"Municípios da RMB carregados: {len(rmb_codes)}")
    return rmb_codes

def main():
    """
    Converte arquivos DBC do SIH-RD (AIH Reduzida) para CSV.
    
    Conforme especificação do TCC:
    - Origem: data/bronze/sih/*.dbc (arquivos já baixados)
    - Destino: data/bronze/sih/csv/*.csv
    - Estado: Pará (PA)
    - Período: 2015-2025
    - Tipo: AIH Reduzida (RD)
    - Foco: Municípios da RMB
    """
    # Configurações
    input_dir = Path("data/bronze/sih")
    output_dir = Path("data/bronze/sih/csv")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Verificar se há arquivos DBC
    dbc_files = sorted(input_dir.glob("*.dbc"))
    if not dbc_files:
        print(f"ERRO: Nenhum arquivo DBC encontrado em {input_dir}")
        return
    
    # Carregar municípios da RMB
    rmb_codes = load_rmb_municipalities()
    
    print(f"=" * 70)
    print(f"CONVERSÃO DBC → CSV - SIH-RD (AIH Reduzida) - Pará")
    print(f"=" * 70)
    print(f"Origem: {input_dir.absolute()}")
    print(f"Destino: {output_dir.absolute()}")
    print(f"Arquivos DBC encontrados: {len(dbc_files)}")
    print(f"=" * 70)
    print()
    
    # Estatísticas
    total_arquivos = 0
    total_registros = 0
    total_registros_rmb = 0
    erros = 0
    
    # Converter cada arquivo DBC
    for dbc_file in tqdm(dbc_files, desc="Convertendo DBC → CSV"):
        try:
            # Converter DBC para DataFrame
            df = convert_dbc_to_dataframe(dbc_file)
            
            if df is not None and len(df) > 0:
                total_registros += len(df)
                
                # Identificar registros da RMB
                if rmb_codes is not None and 'MUNIC_RES' in df.columns:
                    # MUNIC_RES contém o código IBGE do município de residência
                    df['is_rmb'] = df['MUNIC_RES'].astype(str).str[:6].astype(int).isin(rmb_codes)
                    total_registros_rmb += df['is_rmb'].sum()
                
                # Salvar como CSV
                csv_filename = output_dir / f"{dbc_file.stem}.csv"
                df.to_csv(csv_filename, index=False, sep=';', decimal=',', encoding='utf-8')
                total_arquivos += 1
                
                rmb_count = df.get('is_rmb', pd.Series([False])).sum() if rmb_codes else 0
                rmb_info = f" ({rmb_count} RMB)" if rmb_codes else ""
                print(f"✓ {csv_filename.name}: {len(df):,} registros{rmb_info}")
            else:
                print(f"✗ {dbc_file.name}: Arquivo vazio")
                erros += 1
                
        except Exception as e:
            erros += 1
            print(f"✗ Erro em {dbc_file.name}: {str(e)[:80]}")
    
    # Resumo final
    print()
    print(f"=" * 70)
    print(f"RESUMO DA CONVERSÃO")
    print(f"=" * 70)
    print(f"Arquivos convertidos: {total_arquivos}/{len(dbc_files)}")
    print(f"Total de registros: {total_registros:,}")
    if rmb_codes and total_registros > 0:
        print(f"Registros da RMB: {total_registros_rmb:,} ({total_registros_rmb/total_registros*100:.1f}%)")
    print(f"Erros: {erros}")
    print(f"Destino: {output_dir.absolute()}")
    print(f"=" * 70)
    
    # Resumo final
    print()
    print(f"=" * 70)
    print(f"RESUMO DA CONVERSÃO")
    print(f"=" * 70)
    print(f"Arquivos convertidos: {total_arquivos}/{len(dbc_files)}")
    print(f"Total de registros: {total_registros:,}")
    if rmb_codes and total_registros > 0:
        print(f"Registros da RMB: {total_registros_rmb:,} ({total_registros_rmb/total_registros*100:.1f}%)")
    print(f"Erros: {erros}")
    print(f"Destino: {output_dir.absolute()}")
    print(f"=" * 70)

if __name__ == "__main__":
    main()
