# Status do MVP "RMB Saneamento + Saúde" (Planejado vs Execução)

Atualização: 18/11/2025

Este documento resume o que foi planejado nos artefatos oficiais (`docs/projeto-final-curso-i2a2`, `docs/roteiro_analises_modelagem_dashboard.md` e guias associados) e o que foi efetivamente entregue pelos notebooks `analise_exploratoria_IA2A.ipynb`, `modelagem_IA2A.ipynb` e pelo dashboard atual (`dashboard/material_para_dashboard/RMB_Saneamento+Saúde_(MVP_COP30).pdf`). O objetivo é tornar visíveis os desvios que estão impedindo a publicação final do dashboard e alinhar os próximos passos.

## 1. Quadro comparativo

| Pilar | Planejado (docs/) | Executado (nov/2025) | Desvios / Impacto |
| --- | --- | --- | --- |
| **Camadas de dados** | ETL bronze→silver→gold completo, com `gold_features_ano`, `snis_rmb_indicadores_v2`, `gold_qualidade_agua` alimentando notebooks/dash | Camadas bronze/silver/gold prontas; notebooks continuam lendo apenas Silver via caminhos do Google Drive | Falta consumir diretamente os arquivos Gold; dependência de `/content/drive/...` quebra reprodutibilidade local e impede automatizar exports para o dashboard |
| **EDA (Visão executiva, Saúde & Clima, Qualidade, Operação)** | Notebook deveria consolidar indicadores anuais/mensais, responder perguntas de negócio e gerar tabelas/visualizações para o Looker | `analise_exploratoria_IA2A.ipynb` faz inventário e análises gerais (histogramas, sazonalidade, correlação) apenas com Silver; não produz datasets de saída nem cruza clima com saúde por lag | Painel de Saúde & Clima e ODS Tracker ficam sem feeds; necessidades de priorização não são respondidas |
| **Modelagem / Painel de Prioridade** | Notebook deveria usar `gold_features_ano`, testar Regressão Linear, Lasso, RandomForest com k-fold, explicar importâncias, estimar elasticidades e gerar ranking 12 meses + simulador | `modelagem_IA2A.ipynb` carrega CSV manual via `files.upload()`, treina modelos básicos, calcula importâncias e correlações, porém não salva outputs, não projeta cenários, não gera ranking nem integra clima (lags) | Sem coeficientes/elasticidades exportados → Painel de Prioridade e simulador não existem; perguntas #1-4 permanecem sem evidências mensuráveis |
| **ODS Tracker** | Página dedicada com indicadores ODS 6/3/11 (+ metas e status) usando Gold + SNIS/IBGE | Não há cálculo de KPIs ODS em nenhum notebook; dashboard PDF usa placeholders | Avaliadores não conseguem verificar aderência às ODS; requisito central do TCC sem cobertura |
| **Dashboard (Looker Studio)** | Páginas: Visão RMB, Saúde & Clima, Qualidade, Operação, Painel Priorizar & Simular, ODS Tracker, com filtros e metas | MVP em PDF mostra apenas parte das páginas, com indicadores estáticos; dados alimentados manualmente | Falta pipeline automatizado; sem simulador, sem ODS, sem integrações com outputs dos notebooks |

## 2. Detalhes por notebook

### `analise_exploratoria_IA2A.ipynb`
- **Dependência externa**: monta Google Drive e referencia `/content/drive/MyDrive/silver/...` — inviável fora do Colab e sem parametrização.
- **Escopo limitado**: foca nas bases Silver (INMET, SIH, SISAGUA, SIOPS, Pop) e ignora `data/gold/`, `snis_rmb_indicadores_v2` e `gold_qualidade_agua` citados na documentação.
- **Perguntas em aberto**: não há análise cruzada clima × saúde com defasagens, nem ranking por retorno sanitário, nem indicadores ODS.
- **Ausência de exports**: gráficos são apenas exibidos/salvos localmente (`*.png`), mas não há CSV/Parquet com métricas para o Looker Studio.

### `modelagem_IA2A.ipynb`
- **Carregamento manual**: depende de `files.upload()` e de um CSV fora do repositório, quebrando o princípio de reprodutibilidade.
- **Pré-processamento**: remove colunas com muitos NaNs sem documentar; não garante que `gold_features_ano` seja a base oficial; não há split temporal ou validação k-fold como planejado.
- **Resultados não persistidos**: métricas (`res_df`), importâncias, previsões por município e análises de precipitação não são exportadas para alimentar o dashboard.
- **Painel de Prioridade**: não há cálculo de elasticidades, score municipal ou simulador; ranking 12 meses é apenas textual.
- **ODS e indicadores de cobertura**: não aparecem.

## 3. Impacto direto no dashboard

1. **Painel de Prioridade / Simulador** depende de coeficientes/elasticidades e de um dataset com score municipal — ainda inexistentes.
2. **Saúde & Clima / Chuvas** não possui séries cruzadas com lags nem narrativa quantitativa (apenas correlação simples).
3. **ODS Tracker** está vazio porque nenhum notebook calcula os KPIs/métodos prometidos.
4. **Atualização automática**: sem arquivos exportados para `dashboard/material_para_dashboard/`, cada atualização exige trabalho manual em planilhas/Looker.

## 4. Plano imediato para realinhamento

| Etapa | Ação | Resultado esperado |
| --- | --- | --- |
| 1 | Refatorar notebooks para detectar automaticamente se estão no Colab ou no repositório local (parametrizar `DATA_ROOT`) | Execução reprodutível em ambos os ambientes, lendo sempre `data/gold/` como fonte oficial |
| 2 | Expandir EDA para gerar tabelas auxiliares (`saude_clima_series`, `eda_municipal`, `qualidade_agua`) e salvar em `dashboard/material_para_dashboard/` | Alimentar diretamente as páginas Visão RMB, Saúde & Clima e Qualidade |
| 3 | Reescrever pipeline de modelagem: usar `gold_features_ano.parquet`, registrar métricas, salvar importâncias, previsões e elasticidades | Basear Painel de Prioridade e simulador em evidências numéricas |
| 4 | Criar notebook/exportador dedicado (`04_export_dashboard_assets.ipynb`) que consolida feeds para Looker (Painel de Prioridade, Saúde & Clima, ODS Tracker) | Garantir atualização rápida do dashboard em cada nova rodada |
| 5 | Atualizar Looker Studio (arquivo `RMB_Saneamento+Saúde_(MVP_COP30).pdf`) conectando os novos feeds e revisando as páginas previstas | Dashboard consistente com o escopo original do TCC |

## 5. Próximos passos encadeados

1. **Documentar ajustes** (este arquivo) e validar com o grupo.
2. **Refatorar notebooks EDA e Modelagem** conforme plano acima (paths parametrizados, uso do Gold, exports).
3. **Construir feed do Painel de Prioridade e ODS Tracker** e armazenar no repositório (`dashboard/material_para_dashboard/`).
4. **Atualizar dashboard no Looker/arquivo PDF** após gerar os dados.

*A Força está nos dados, mas o Poder está na interpretação.* Agora que os desvios estão claros, cada notebook será alinhado à arquitetura planejada para destravar a entrega do dashboard.
