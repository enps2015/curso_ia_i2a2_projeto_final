# RMB Saneamento + Saúde — Console de Decisão (MVP COP30)

> Console orientado a dados para priorizar investimentos em água, esgoto e saúde na Região Metropolitana de Belém, alinhado à COP30 e às ODS 3, 6 e 11.

---

## 1. Storytelling do problema
- **Dor atual**: perdas de água superiores a 40%, cobertura desigual de esgoto e reincidência de não conformidades de qualidade sustentam taxas elevadas de internações por doenças diarreicas (CID A00-A09).
- **Janela de oportunidade**: a COP30 em Belém, a inauguração da ETE Una e o novo arranjo COSANPA + Águas do Pará pressionam por transparência e coordenação regional baseada em evidências.
- **Resposta proposta**: um console de decisão com narrativa clara, modelos explicáveis e indicadores auditáveis que apontem a “próxima melhor ação” por município ou sistema.

## 2. Objetivos do MVP
1. Integrar bases públicas (SISAGUA, SNIS/SINISA, SIH/DATASUS, INMET, IBGE) em pipelines Bronze → Silver → Gold reproducíveis.
2. Quantificar o impacto sanitário de melhorias operacionais (cobertura, perdas, qualidade) com modelos aprendidos no curso.
3. Simular cenários “what-if” e gerar rankings de investimento com explicabilidade.
4. Conectar resultados às metas e indicadores das ODS 3, 6 e 11 para apoiar a governança da RMB.

## 3. Escopo e perguntas de negócio
- **Municípios foco**: Belém, Ananindeua, Marituba, Benevides, Santa Bárbara do Pará, Santa Izabel do Pará, Castanhal e Barcarena.
- **Período trabalhado**: 2018–2025 (ajustável por fonte).
- **Perguntas que guiam o MVP**:
  - Quais alavancas (coleta, tratamento, perdas, qualidade) reduzem mais as internações A00-A09?
  - Qual o ranking de priorização de investimentos por município nos próximos 12 meses?
  - Como a chuva e as ondas de calor modulam o risco sanitário ao longo do ano?
  - Qual o retorno sanitário e financeiro por ponto percentual de melhoria?
  - Como monitorar a evolução nas ODS 3/6/11 com indicadores comparáveis?

## 4. Entregáveis
- Dossiê narrativo em `docs/projeto-final-curso-i2a2` + resumos rápidos em `docs/resumo_insights.md` e `docs/briefing_orientador.md`.
- Guias operacionais/ETL atualizados (`docs/Guia de Preparação...`, `docs/Guia Operacional...`, `docs/roteiro_analises_modelagem_dashboard.md`).
- Scripts ETL em `scripts/` para regenerar Bronze→Silver e o `silver_to_gold_features.py` para o dataset consolidado.
- Notebooks finais (`notebooks/analise_exploratoria_IA2A.ipynb` e `notebooks/modelagem_IA2A.ipynb`) com os experimentos usados na apresentação.
- Pasta `dashboard/` com assets e exports do Looker Studio.
- Tabelas Gold oficiais: `data/gold/snis_rmb_indicadores_v2.{csv,parquet}` e `data/gold/gold_features_ano.{csv,parquet}`.

## 5. Arquitetura de dados
| Camada | O que contém | Como produzir |
| --- | --- | --- |
| **Bronze** | Dados brutos (CSV, ZIP, DBC, DBF) em `data/bronze/<fonte>/` | Download manual ou scripts dedicados, preservando os originais. |
| **Silver** | Parquets padronizados com chaves `cod_mun`, `municipio`, `ano` | `bronze_to_silver_*.py` e `inmet_to_parquet.py` com `--input-dir`/`--output-dir`. |
| **Gold** | Indicadores prontos para análise, modelos e dashboard | `silver_to_gold_features.py`, `etl_snis_indicadores_rmb.py` e agregadores específicos. |

> A consistência de chaves é garantida por `config/rmb_municipios.csv`, que mapeia códigos IBGE, proxies INMET e aliases SISAGUA.

## 6. Fontes e variáveis principais
- **SISAGUA/VIGIÁGUA**: cloro residual, turbidez, pH, % de amostras conformes.
- **SNIS/SINISA**: cobertura de água/esgoto, perdas na distribuição, % de esgoto tratado, indicadores econômico-financeiros.
- **SIH/DATASUS**: internações mensais CID A00-A09 (denominador IBGE) e custos hospitalares.
- **INMET**: chuva acumulada e dias de calor extremo (percentil 90) com defasagens.
- **IBGE/SIDRA 6579 + Censo 2022**: população, condições domiciliares e saneamento.

A matriz ODS → KPI → Fonte está documentada em `docs/projeto-final-curso-i2a2` e replicada no dashboard.

## 7. Stack tecnológica
- **Linguagem e ambiente**: Python 3.10+, `venv`, dependências em `requirements.txt`.
- **Ingestão**: `requests`, `ckanapi`, utilitários (`scripts/ckan_fetch_dataset.py`, `sih_rd_download_pa.py`).
- **Processamento**: `pandas`, `pyarrow`, `polars` (opcional), `dbfread`, conversores DBC/DBF.
- **Modelagem (notebooks a produzir)**: `scikit-learn`, `statsmodels`, `shap`, `yellowbrick`.
- **Storytelling**: Jupyter (VS Code) e dashboard Looker Studio.
- **Governança**: Git + GitHub (`main`, branches `feature/<slug>`).

## 8. Estrutura do repositório
```
.
├── config/                   # Dicionários e mapeamentos (ex.: rmb_municipios.csv)
├── data/
│   ├── bronze/               # Dados brutos organizados por fonte (não versionados)
│   ├── silver/               # Artefatos Parquet padronizados
│   └── gold/                 # Features finais (CSV/Parquet)
├── docs/                     # Dossiê, guias operacionais, relatos
├── notebooks/                # EDA, modelagem, simulador (a desenvolver)
├── dashboard/                # Exports do painel (PNG, PDF, links)
├── scripts/                  # Pipelines ETL e utilitários
├── requirements.txt          # Dependências Python
└── README.md
```

## 9. Como reproduzir em 7 passos
1. **Criar ambiente**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Organizar Bronze** em `data/bronze/<fonte>/` (ver exemplos no guia operacional).
3. **Gerar Silver** com `bronze_to_silver_*.py` e `inmet_to_parquet.py`, ajustando diretórios.
4. **Gerar Gold** com `etl_snis_indicadores_rmb.py` e `silver_to_gold_features.py` (ver docstrings).
5. **Rodar smoke tests** usando `--output-dir /tmp/<slug>` para evitar sobrescrever artefatos oficiais.
6. **Construir notebooks** seguindo `docs/roteiro_analises_modelagem_dashboard.md` (EDA → modelagem → simulador).
7. **Atualizar o dashboard**: publicar no Looker Studio, exportar para `dashboard/` e registrar o link.

## 10. Roadmap imediato
1. **Congelar dados**: manter `data/gold/gold_features_ano.*` e `snis_rmb_indicadores_v2.*` alinhados à versão apresentada (rodar `silver_to_gold_features.py` apenas se chegar dado novo).
2. **Executar notebooks finais**: rodar `analise_exploratoria_IA2A.ipynb` e `modelagem_IA2A.ipynb` com kernels limpos, exportar gráficos/tabelas para `docs/` e `dashboard/`.
3. **Atualizar dashboard**: publicar a versão mais recente no Looker Studio, salvar exports (PDF/PNG) e registrar links em `dashboard/material_para_dashboard/`.
4. **Compartilhar documentação**: garantir que os guias em `docs/` e este README reflitam a rodada vigente; anexar briefing/resumo aos canais da banca/orientador.
5. **Preparar storytelling/pitch**: usar os insights consolidados (docs/resumo_insights.md + dashboard) para alimentar apresentação e relatório final.

## 11. Documentação complementar
- `docs/projeto-final-curso-i2a2` — dossiê oficial com storytelling completo e rastreabilidade ODS.
- `docs/roteiro_analises_modelagem_dashboard.md` — passo a passo para EDA, modelagem, simulador e dashboard.
- `docs/relato_coleta_tratamento.md` — entraves, soluções e lições aprendidas.
- `docs/Guia de Preparacao de Dados - TCC Agua, Saneamento e Saude na RMB_PA.md` — instruções detalhadas de ETL e governança.

## 12. Contribuição e boas práticas
- Trabalhar em branches `feature/<slug>` e abrir PRs pequenos com contexto.
- Não versionar dados brutos; manter backups externos confiáveis.
- Documentar novas features ou notebooks neste README ou nos guias correspondentes.
- Abrir issues para dúvidas ou bugs, indicando fonte, cenário e expectativa.

## 13. Equipe e contato
- (Inserir nomes, papéis e contatos da equipe)

---

> Este repositório é a base do MVP apresentado à banca I2A2. Evoluções devem preservar a arquitetura Bronze/Silver/Gold, a rastreabilidade das fontes públicas e o compromisso com transparência para a RMB.
