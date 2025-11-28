# Guia de referência – `notebooks/analise_exploratoria_IA2A.ipynb`

Este documento explica o propósito de cada seção do notebook de análises exploratórias, relaciona as perguntas de negócio e resume os principais insights esperados para alimentar o dashboard no Looker Studio.

## Contexto geral

- **Escopo**: 8 municípios da Região Metropolitana de Belém (RMB) – Belém, Ananindeua, Marituba, Benevides, Santa Bárbara do Pará, Santa Izabel do Pará, Castanhal e Barcarena – para os anos de 2018 a 2025.
- **Fontes principais**: `data/gold/gold_features_ano.parquet`, `data/gold/snis_rmb_indicadores_v2.parquet`, `data/silver/ibge_populacao/populacao.parquet` e `config/rmb_municipios.csv`.
- **Saídas obrigatórias**: `dashboard/material_para_dashboard/painel_prioridade.csv` (Painel Prioridade) e `dashboard/material_para_dashboard/ods_tracker.csv` (ODS Tracker).
- **Perguntas de negócio cobertas** (doc `docs/roteiro_analises_modelagem_dashboard.md`):
  1. Quais ações reduzem mais as internações?
  2. Qual o retorno por município/sistema?
  3. Como a chuva modula o risco?
  4. Qual o ranking de priorização para os próximos 12 meses?
  5. Como estamos frente às metas ODS 6/3/11?

## Passo a passo do notebook

| # | Célula | Descrição | Perguntas respondidas |
|---|--------|-----------|------------------------|
| 1 | Configuração do ambiente | Resolve `PROJECT_ROOT` (local/Colab), define `DATA_DIR`, `SILVER_DIR`, `GOLD_DIR` e cria `dashboard/material_para_dashboard`. Garante reprodutibilidade para toda a equipe. | – |
| 2 | Snapshot da Gold | Lê `gold_features_ano.parquet`, imprime nº de registros e exibe as 10 primeiras linhas. Confirma integridade das colunas/anos antes de derivar métricas. | 1–5 (pré-condição) |
| 3 | População Silver | Lê `data/silver/ibge_populacao/populacao.parquet`, normaliza `cod_mun` e cruza com `config/rmb_municipios.csv`. Verifica se os 8 municípios esperados estão presentes. | 4–5 |
| 4 | Preparação analítica | Cria `RMB_CFG`, mergeia Gold com SNIS (fallback para preencher lacunas de serviço) e valida cobertura de 2018–2025 (8×8 garantido). Já emite alerta caso `gold_qualidade_agua.*` não exista. | 1–5 |
| 5 | Métricas e insights | - Preenche valores ausentes via mediana municipal.
  - Mantém percentuais entre 0–100.
  - Cria variáveis de ação: `deficit_atendimento`, `deficit_tratamento`, `alerta_qualidade`, `perdas_excesso`, `chuva_total_mm_lag1`.
  - Calcula `score_priorizacao` (pesos: 40% taxa hídrica, 20% déficit tratamento, 15% alerta qualidade, 15% déficit atendimento, 10% perdas) e classifica Estável/Atenção/Crítico.
  - Produz drivers de correlação, ranking 2025, retorno médio por município (incluindo elasticidade investimentos × taxa) e agrega o `ods_tracker` com metas.
  - Marca cada KPI com status OK/Alerta segundo limites: taxa ≤ 30 (por 10k hab.), `pct_conformes_global` ≥ 95, `idx_atend_agua_total` ≥ 95, `idx_tratamento_esgoto` ≥ 80.
  - Destaques observados: correlação positiva de chuva total (0,41) e negativa de % investimento em saúde (-0,34); Ananindeua lidera taxa média e tem elasticidade -0,84 (investimento reduz taxa); Belém mantém cobertura elevada porém tratamento próximo de 0; ODS Tracker mostra gargalos em qualidade e tratamento para todos os anos.
 | 1–5 |
| 6 | Exportação para o Looker | Salva `painel_prioridade.csv` (todos os campos usados no Painel Prioridade + `score_priorizacao`, `prioridade_categoria` e `gerado_em` em UTC) e `ods_tracker.csv` (indicadores agregados, metas e status por ano, também com timestamp). Esses arquivos são a fonte única do dashboard. | 4–5 |

## Insights esperados e narrativa para o dashboard

1. **Drivers de internações (Pergunta 1)**
   - Déficit de tratamento e baixa conformidade na água aparecem com correlação positiva significativa em relação à taxa de internações hídricas.
   - Investimento per capita e % de investimentos em saúde apresentam correlação negativa, sugerindo retorno quando o município direciona recursos para infraestrutura e vigilância.

2. **Retorno por município (Pergunta 2)**
   - A tabela `retorno_municipal` evidencia municípios com maior elasticidade negativa (Ananindeua, Marituba), indicando onde o ganho marginal por ponto de investimento é maior.
   - Municípios com elasticidade positiva ou baixa (Belém, Benevides) precisam de ações estruturantes (coleta/tratamento) além de gasto corrente.

3. **Influência climática (Pergunta 3)**
   - A correlação de 0,349 entre chuva com lag de 1 ano e taxa sugere efeitos retardados de chuvas fortes na incidência de agravos hídricos. Esse insight orienta a criação de alertas sazonais no dashboard.

4. **Ranking e priorização (Pergunta 4)**
   - `painel_prioridade.csv` ordena municípios pelo `score_priorizacao` e atribui as categorias Estável/Atenção/Crítico.
   - O ranking 2025 mostra Ananindeua como crítico, seguido por Belém e Santa Izabel. Esses resultados alimentam diretamente a aba “Priorizar & Simular”.

5. **ODS 6/3/11 (Pergunta 5)**
   - O `ods_tracker` exibe por ano: população total, internações totais, médias de atendimento/tratamento/conformidade, % de investimentos e chuvas. Cada indicador recebe status OK/Alerta com base nas metas documentadas.
   - Observação atual: metas de tratamento (80%) e conformidade (95%) não são atingidas em nenhum ano, reforçando mensagens-chave para a banca.

## Como utilizar

1. Execute o notebook completo (kernel limpo) para atualizar análises e exports:
   ```bash
   jupyter nbconvert --execute --inplace notebooks/analise_exploratoria_IA2A.ipynb
   ```
2. Verifique os CSVs em `dashboard/material_para_dashboard/` e atualize a fonte no Looker Studio.
3. Use os quadros “Drivers”, “Ranking” e “ODS Tracker” deste notebook para construir a narrativa textual do relatório.

Com este guia, qualquer integrante consegue reproduzir o notebook, entender a lógica das métricas e justificar os insights no relatório final e no dashboard. Ajustes futuros (novas fontes ou indicadores) devem ser registrados aqui e no roteiro em `docs/`. 
