# Guia de referência – `notebooks/modelagem_IA2A.ipynb`

Este guia descreve a etapa de modelagem preditiva construída para complementar o notebook exploratório. O objetivo é estimar a taxa de internações por agravos hídricos (por 10 mil habitantes) com base nos drivers de saneamento, qualidade da água, clima e finanças municipais, responder às perguntas 1, 2 e 4 do roteiro e alimentar as páginas restantes do dashboard no Looker Studio.

## Resumo rápido

- **Escopo temporal/geográfico**: mesmos 8 municípios da RMB (2018‑2025). O ano de 2025 é reservado como holdout para avaliação temporal e depois reintegrado para previsões completas.
- **Camadas usadas**: `data/gold/gold_features_ano.parquet` + fallback `data/gold/snis_rmb_indicadores_v2.parquet`, enriquecidas com `config/rmb_municipios.csv` para manter o mesmo `analysis_df` do notebook exploratório.
- **Modelos avaliados**: Regressão Linear, Lasso e Random Forest com pipelines (imputação mediana + padronização). GroupKFold (k=4) por município evita vazamento entre cidades.
- **Modelo selecionado**: Random Forest (MAE CV ≈ 4,8 / RMSE CV ≈ 6,3). No holdout 2025, MAE = 4,18 e RMSE = 5,46 (R² negativo indica que oscilações 2025 são pouco explicadas, então os resultados devem ser usados como tendência relativa, não previsão pontual).
- **Explicabilidade**: importâncias do modelo e por permutação apontam `populacao`, `despesa_saude_pc`, `pct_conformes_global` e variáveis climáticas como principais drivers. Elasticidades simulam ganhos médios ao elevar atendimento/tratamento/qualidade em +5 p.p. e investimentos em +0,5 p.p.
- **Exports gerados**: `modelagem_metricas.csv`, `modelagem_importancias.csv`, `modelagem_previsoes.csv` e `modelagem_cenarios.csv` (todos em `dashboard/material_para_dashboard/`) abastecem as páginas “Priorizar & Simular” e “Elasticidades” do dashboard.

## Fluxo por seção

| # | Seção do notebook | Descrição | Artefatos / Perguntas |
|---|-------------------|-----------|------------------------|
| 1 | Configuração do ambiente | Resolve `PROJECT_ROOT` (local/Colab), importa bibliotecas e garante criação de `dashboard/material_para_dashboard`. | Pré-condição |
| 2 | Leitura da Gold + fallback SNIS | Carrega `gold_features_ano.parquet`, aplica preenchimento a partir do SNIS (colunas de serviço) e verifica cobertura 8×8 para 2018‑2025. | 1, 2, 4 |
| 3 | Construção do `analysis_df` | Replica o preparo do notebook exploratório (preenchimentos, derivação de déficits, `score_priorizacao`, `chuva_total_mm_lag1`). Mantém consistência entre análise e modelagem. | 1, 2, 4 |
| 4 | Seleção de features e target | Define `internacoes_hidricas_10k` como alvo e escolhe 21 variáveis acionáveis (cobertura, perdas, clima, gastos). Resulta em 64 linhas (8 municípios × 8 anos). | 1, 2 |
| 5 | GroupKFold por município | Avalia Linear, Lasso e RandomForest usando pipelines `SimpleImputer + StandardScaler`. RandomForest vence com MAE CV 4,77 e estabilidade entre folds. | 1 |
| 6 | Holdout 2025 + previsões | Treina no período 2018‑2024, mede desempenho em 2025 e, em seguida, refita o modelo em todo o histórico para gerar `pred_all`. Produz tabela de erros por município/ano para a narrativa. | 2, 4 |
| 7 | Importâncias e elasticidades | Calcula importâncias internas e por permutação; simula +5 p.p. em cobertura/tratamento/qualidade e +0,5 p.p. em investimentos/finanças para estimar impacto médio na taxa prevista. | 1, 2 |
| 8 | Export para dashboard | Escreve CSVs de métricas, importâncias, previsões históricas e cenários (todos com `gerado_em` em UTC). | 4 |

## Resultados relevantes para o storytelling

- **Desempenho**: o RF reduz o MAE para ~4 casos por 10k hab. no holdout, mas mantém R² negativo. Use os valores previstos como tendência/contrafactual e destaque a baixa quantidade de observações (64 pontos) como limitação.
- **Drivers**: `populacao`, `pct_transferencias_sus_recursos`, `despesa_saude_pc`, `pct_conformes_global`, clima (chuva/temperatura) e `umid_rel_media_pct` concentram >80% da importância acumulada. Isso ajuda na resposta da pergunta 1 (quais ações reduzem mais as internações) ao mostrar que infraestrutura + clima ainda lideram.
- **Elasticidades simuladas**: elevar `pct_conformes_global` em +5 p.p. reduziria a taxa prevista em ~0,19 por 10k em média; ganhos similares acontecem com cobertura e tratamento (+0,11/+0,12). Investir +0,5 p.p. em `% despesa investimentos` gera efeito médio -0,009 (pequeno porque a série histórica tem baixa variância). Esses números alimentam os cartões “quanto precisamos mover cada indicador para reduzir X internações”.
- **Ranking reponderado**: `modelagem_previsoes.csv` contém `taxa_observada`, `taxa_prevista`, `erro_absoluto` e `prioridade_categoria`. Combine com o `painel_prioridade.csv` para contar a história de “prioridades x surpresas do modelo” na banca.

## Arquivos gerados para o Looker

| Arquivo | Campos principais | Uso no dashboard |
|---------|-------------------|------------------|
| `dashboard/material_para_dashboard/modelagem_metricas.csv` | `model`, `dataset`, `mae`, `rmse`, `r2`, `gerado_em` | Tabela de comparação (CV vs Holdout). |
| `dashboard/material_para_dashboard/modelagem_importancias.csv` | `feature`, `valor`, `tipo`, `gerado_em` | Gráfico combinado de importâncias (modelo vs permutação). |
| `dashboard/material_para_dashboard/modelagem_previsoes.csv` | `cod_mun`, `municipio`, `ano`, `taxa_observada`, `taxa_prevista`, `erro_absoluto`, `prioridade_categoria`, `gerado_em` | Série histórica prevista e painel “Desvio por município/ano”. |
| `dashboard/material_para_dashboard/modelagem_cenarios.csv` | `feature`, `delta_aplicado`, `impacto_medio_taxa`, `impacto_min_taxa`, `impacto_max_taxa`, `gerado_em` | Cards de elasticidade/what-if. |

## Como atualizar

1. Garanta que o ambiente virtual esteja ativo (`source .venv/bin/activate`) e que `scikit-learn` esteja instalado (o notebook chama `pip install` automaticamente se faltar).
2. Execute todas as células do notebook ou rode:
   ```bash
   jupyter nbconvert --execute --inplace notebooks/modelagem_IA2A.ipynb
   ```
3. Verifique os quatro CSVs na pasta `dashboard/material_para_dashboard/` e atualize a fonte do Looker Studio.
4. Documente eventuais ajustes de features/hiperparâmetros aqui e em `docs/roteiro_analises_modelagem_dashboard.md` para manter a rastreabilidade com a banca.

Com este documento, qualquer integrante consegue entender o racional do modelo, reproduzir as métricas e explicar as limitações/insights resultantes para a banca e para o relatório final.
