# Resumo integrado de insights (EDA + Modelagem)

Este documento resume todas as conclusões extraídas dos notebooks `notebooks/analise_exploratoria_IA2A.ipynb` (EDA) e `notebooks/modelagem_IA2A.ipynb` (modelagem preditiva). A ideia é que qualquer membro do grupo — mesmo sem experiência prévia em IA — consiga explicar os resultados ao professor mentor e utilizar os dados no dashboard do Looker Studio.

## 1. Estado geral do projeto

- **Cobertura de dados**: 8 municípios da Região Metropolitana de Belém (Belém, Ananindeua, Marituba, Benevides, Santa Bárbara do Pará, Santa Izabel do Pará, Castanhal e Barcarena), de 2018 a 2025. Todos os 64 pares município/ano estão presentes após o merge com SNIS.
- **Camadas e arquivos usados**:
  - Gold: `data/gold/gold_features_ano.parquet` (base principal) + `gold_qualidade_agua` (já incorporada) + fallback `snis_rmb_indicadores_v2.parquet` para preencher lacunas de atendimento/tratamento.
  - Configuração: `config/rmb_municipios.csv` para garantir IBGE codes e nomes padronizados.
  - Exportações prontas para o dashboard:
    - `dashboard/material_para_dashboard/painel_prioridade.csv`
    - `dashboard/material_para_dashboard/ods_tracker.csv`
    - `dashboard/material_para_dashboard/modelagem_metricas.csv`
    - `dashboard/material_para_dashboard/modelagem_importancias.csv`
    - `dashboard/material_para_dashboard/modelagem_previsoes.csv`
    - `dashboard/material_para_dashboard/modelagem_cenarios.csv`
- **Perguntas de negócio cobertas** (doc `docs/roteiro_analises_modelagem_dashboard.md`):
  1. Quais ações reduzem mais as internações?  
  2. Qual o retorno por município/sistema?  
  3. Como a chuva modula o risco?  
  4. Quais municípios priorizar nos próximos 12 meses?  
  5. Como está a RMB frente às metas ODS 6/3/11?

## 2. Principais descobertas da Análise Exploratória (EDA)

1. **Drivers de internações (Pergunta 1)**
   - Correlação positiva forte entre `internacoes_hidricas_10k` e variáveis de déficit de saneamento: `deficit_tratamento`, `deficit_atendimento`, `alerta_qualidade` (construção: 100 – índice).
   - Investimento em saúde (`pct_despesa_investimentos_saude` e `despesa_saude_pc`) apresenta correlação negativa moderada (mais investimento tende a reduzir a taxa).
   - `perdas_excesso` (derivado de `idx_perdas_distribuicao`) indica descuido operacional e aparece entre os componentes do score de priorização.

2. **Retorno financeiro por município (Pergunta 2)**
   - Tabela `retorno_municipal`: resume taxa média, investimento médio e elasticidade investimento × taxa.  
   - Exemplo: Ananindeua e Marituba têm elasticidades negativas mais fortes (aprox. –0,8), indicando que cada ponto percentual adicional de investimento em saúde traz queda perceptível na taxa de internações.

3. **Influência climática (Pergunta 3)**
   - Correlação entre chuva total (lag de 1 ano) e taxa hídrica ≈ 0,35: períodos de chuva intensa antecedem picos de internações.  
   - `chuva_total_mm_lag1` é usado tanto na análise quanto no modelo para capturar esse efeito retardado.

4. **Ranking e priorização (Pergunta 4)**
   - Score de priorização (peso 40% taxa hídrica, 20% déficit tratamento, 15% alerta qualidade, 15% déficit atendimento, 10% perdas) gera categorias Estável / Atenção / Crítico.  
   - Ano mais recente (2025) mostra Ananindeua, Belém e Santa Izabel como casos críticos, enquanto Castanhal e Barcarena aparecem como mais estáveis.

5. **ODS Tracker (Pergunta 5)**
   - Metas aplicadas: taxa ≤ 30 intern/10k, cobertura de água ≥ 95%, tratamento ≥ 80%, qualidade ≥ 95%.  
   - Resultado: praticamente todos os anos têm status “Alerta” em tratamento e qualidade; apenas cobertura de água se aproxima das metas, reforçando a narrativa de gargalos estruturais.

## 3. Principais resultados da Modelagem Preditiva

1. **Setup dos modelos**
   - Target: `internacoes_hidricas_10k`.  
   - Features (21 no total) incluem índices de cobertura/tratamento/coleta, perdas, clima, despesas em saúde, percentuais financeiros (SUS, receita própria, despesa com medicamentos/pessoal) e população.  
   - Pipelines com `SimpleImputer(median)` + `StandardScaler`, avaliados com GroupKFold (k=4) por município para evitar vazamento.

2. **Desempenho**
   - Random Forest superou Linear e Lasso (MAE CV ≈ 4,77; RMSE ≈ 6,30).  
   - Holdout temporal em 2025: MAE = 4,18, RMSE = 5,46, R² = –4,92 (R² negativo porque o período de 2025 é volátil e a base tem poucas observações, mas o MAE mostra que as previsões estão dentro de ~4 casos por 10 mil hab.).
   - Conclusão prática: usar o modelo como ferramenta de tendência/contrafactual, não como previsão pontual precisa.

3. **Importâncias e explicabilidade**
   - Importância do modelo: `populacao`, `% transferências SUS`, `% despesa pessoal em saúde`, `despesa_saude_pc`, `% receita própria ASPS`, `chuva_total_mm` e `umid_rel_media_pct` compõem >80% da importância acumulada.  
   - Permutation importance confirma `populacao`, `despesa_saude_pc`, `temp_media_c`, `pct_conformes_global` e `alerta_qualidade` como top drivers.

4. **Elasticidades simuladas**
   - Simulação +5 p.p. em `pct_conformes_global` reduz a taxa projetada em ~0,19 por 10k hab. (média).  
   - Melhorias de +5 p.p. em `idx_atend_agua_total` e `idx_tratamento_esgoto` geram reduções médias de ~0,11 / 0,12 por 10k hab.  
   - Incrementos de +0,5 p.p. em `% despesa investimentos em saúde` têm impacto pequeno (–0,009) porque a série histórica tem baixa variação nesse indicador — insight importante para orientar o discurso: precisamos de saltos maiores ou alocação direcionada.

5. **Exportações para o dashboard**
   - `modelagem_metricas.csv`: métricas de CV e holdout, com timestamp.  
   - `modelagem_importancias.csv`: tabela combinada (feature importance + permutation).  
   - `modelagem_previsoes.csv`: série histórica com `taxa_observada`, `taxa_prevista`, `erro_absoluto` e `prioridade_categoria`.  
   - `modelagem_cenarios.csv`: resumo das elasticidades.

## 4. Requisitos para o dashboard

- **Painel Prioridade** (Looker): alimentado por `painel_prioridade.csv` + `modelagem_previsoes.csv` para mostrar ranking atual e comportamento previsto/observado.
- **ODS Tracker**: usa `ods_tracker.csv` diretamente (por ano, metas, status).  
- **Seção de Insights/Elasticidades**: combina `modelagem_metricas.csv`, `modelagem_importancias.csv`, `modelagem_cenarios.csv` para construir cards de desempenho de modelo, gráficos de importância e blocos “e se?”.
- **Narrativa**: todas as descrições acima (incluindo limitações como R² negativo) devem acompanhar os dashboards para orientar a interpretação dos resultados.

## 5. Mensagem para a reunião das 18h

1. **Estamos alinhados com o plano inicial**: dados consolidados, lacunas preenchidas, exports atualizados e documentação (`docs/analise_exploratoria_notebook.md`, `docs/modelagem_notebook.md` e este arquivo) permitem que qualquer membro reproduza o processo.
2. **O que falta**: apenas ajustes finos caso queiramos melhorar o R² do modelo (ex.: testar mais hiperparâmetros ou adicionar lags/variáveis derivadas). Mas para a banca, já temos material completo para o dashboard e para sustentar as cinco perguntas de negócio.
3. **Próximos passos**:  
   - Subir os CSVs ao Looker (ou atualizar as fontes existentes).  
   - Preparar os slides da reunião usando este resumo como guia.  
   - Validar junto ao professor se a granularidade e justificativas são suficientes ou se devemos aprofundar análises causais.

Com isso, tanto a equipe quanto o professor têm um panorama detalhado do que foi feito e de como os resultados se conectam ao objetivo do TCC.
