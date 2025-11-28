# Catálogo de Dados – RMB (TCC Saneamento & Saúde)

**Escopo:** bases públicas, acessíveis, com foco na Região Metropolitana de Belém (RMB). Colunas indicam se há **script funcional** no pack e **como baixar** quando manual.

| Fonte | Conjunto de dados | Link público | Método | Como baixar | Etapa do TCC e uso |
| --- | --- | --- | --- | --- | --- |
| OPENDATASUS/CKAN | **SISAGUA – Controle Mensal – Parâmetros Básicos** | https://opendatasus.saude.gov.br/dataset/sisagua-controle-mensal-parametros-basicos | **Script** | python scripts/sisagua_download.py (baixa via CKAN). Filtrar RMB depois. | Bronze (ingestão); Prata (limpeza/filtragem RMB); Ouro (agregações mensais; indicadores de QdA). |
| OPENDATASUS/CKAN | **SISAGUA – Controle Mensal – Demais Parâmetros** | https://opendatasus.saude.gov.br/dataset/sisagua-controle-mensal-demais-parametros | **Script** | python scripts/sisagua_download.py (CKAN). | Complementar variáveis de QdA; análises de não conformidade. |
| OPENDATASUS/CKAN | **SISAGUA – Vigilância – Demais Parâmetros** | https://opendatasus.saude.gov.br/dataset/sisagua-vigilancia-demais-parametros | **Manual/Script genérico** | Pode usar ckan_fetch_dataset.py --slug sisagua-vigilancia-demais-parametros (quando houver recursos CSV/ZIP). | Cruzamento com Controle Mensal; checagens de risco. |
| OPENDATASUS/CKAN | **SISAGUA – Controle Mensal – Infraestrutura Operacional** | https://opendatasus.saude.gov.br/dataset/sisagua-controle-mensal-infraestrutura-operacional | **Manual/Script genérico** | ckan_fetch_dataset.py --slug sisagua-controle-mensal-infraestrutura-operacional (baixa todos recursos). | Metadados operacionais para análises de resiliência. |
| DATASUS/FTP | **SIH/SUS – AIH Reduzida (RD)** | ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/ (e pasta 199201_200712) | **Script** | python scripts/sih_rd_download_pa.py --year-start 2015 --year-end 2025 (PA). Depois dbc_to_csv.py. | Séries de internações sensíveis a água (CID A00–A09), agregação mensal por município. |
| IBGE/SIDRA | **Tabela 6579 – População residente (estimativas)** | https://apisidra.ibge.gov.br/values/t/6579 | **Script** | python scripts/sidra_population_download.py --years 2001-2025 (gera CSV por ano p/ RMB). | Denominadores para taxas/100 mil hab. |
| INMET – BDMEP | **Meteorologia diária (chuva, Tmáx/Tmín, etc.)** | https://bdmep.inmet.gov.br/ | **Manual/API** | Requer cadastro/token para API. Alternativa: usar BigQuery da Base dos Dados (ver README geral). | Covariáveis climáticas para modelos; defasagens chuva→desfecho. |
| Base dos Dados (BigQuery) | **INMET/BDMEP (espelho BD)** | https://basedosdados.github.io/mais/access_data_bq/ | **Manual (SQL)** | Consultar via BigQuery Web UI; exportar CSV. | Idem acima; facilita automação sem login do INMET. |
| SNIS (Ministério das Cidades) | **Diagnósticos/Planilhas – Água & Esgoto** | https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/snis | **Manual** | Acessar “Tabelas/Planilhas” por ano; baixar XLSX e filtrar PA/RMB. | Contexto de cobertura, perdas, atendimento; validação cruzada. |
| SIOPS (MS) | **Receitas/Despesas em Saúde (Municípios)** | https://www.gov.br/saude/pt-br/acesso-a-informacao/siops/indicadores | **Manual (TabNet/Web)** | Usar consultas e exportar CSV por município/ano (RMB). | Proxy de capacidade fiscal para priorização. |
| IBGE – Cidades & Estados | **Códigos IBGE e metadados municipais** | https://www.ibge.gov.br/cidades-e-estados | **Manual** | Referência de códigos; já incluído config/rmb_municipios.csv. | Chaves de junção e consistência. |
| SNIRH/ANA | **Atlas Águas & Atlas Esgotos (painéis)** | https://www.snirh.gov.br/portal/snirh-1/paineis-de-indicadores | **Manual** | Consulta online; export por painel (se disponível). | Narrativa de segurança hídrica e esgotamento. |

## Observações

- **Scripts prontos** no Pack: SISAGUA (Parâmetros Básicos e Demais Parâmetros), SIH/RD (PA, 1992–, conforme disponibilidade), conversão DBC→CSV e SIDRA 6579 (população).
- **INMET**: preferir **Base dos Dados (BigQuery)** quando possível; caso use **BDMEP**, será necessário **cadastro/token**.
- **SNIS/SIOPS**: exportação **manual** (interfaces variam), por isso estão sinalizados como _Manual_.
- Arquivo config/rmb_municipios.csv contém **8 municípios** da RMB com **código IBGE** para filtros e junções.