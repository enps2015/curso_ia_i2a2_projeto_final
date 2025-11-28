# **Guia Operacional do TCC – RMB “Água, Saneamento e Saúde”**

**Meta do projeto  
**Construir um protótipo de apoio à decisão que prioriza investimentos de saneamento na Região Metropolitana de Belém (RMB), conectando **serviços de água/esgoto**, **qualidade da água**, **clima**, **saúde** e **gasto público**, com **modelos de IA/ML** e um **dashboard** claro para gestores.

## **1) Objetivo, hipótese e recorte**

- **Unidades de análise:** municípios da RMB – **Belém, Ananindeua, Marituba, Benevides, Santa Bárbara do Pará, Santa Izabel do Pará** – no período **2018–2025** (variando conforme a disponibilidade por fonte).  
    
- **Hipótese central:** melhorias de **cobertura e eficiência dos serviços** (água/esgoto) e **qualidade da água** reduzem **internações por doenças relacionadas** (ex.: diarreias) e **custos**; efeitos são modulados por **chuva e calor**.  
    
- **Resultados esperados:  
    **
    1.  **Rankeamento de prioridades** por município/ano (ou mês),  
        
    2.  **Explicabilidade** (quais fatores pesam mais),  
        
    3.  **Dashboard** com KPIs acionáveis para gestores.  
        

## **2) Alinhamento ao edital/avaliação (professores)**

- **Critério técnico:** dados limpos e integrados; uso apropriado de **regressão/classificação** (do curso); visualizações claras.  
    
- **Impacto socioambiental:** foco em **serviço público local** (água, esgoto, saúde); potencial de **transformação** e **uso real**.  
    
- **Inovação/criatividade:** índice composto e **modelo explicável** (feature importance/SHAP simples).  
    
- **Clareza/comunicação:** relatório de até 8 páginas + apresentação concisa.  
    
- **Escalabilidade/Conexão COP30:** solução replicável a outros municípios e vinculada a **ODS 3 (Saúde), 6 (Água), 11 (Cidades), 13 (Clima)**.  
    

## **3) Estrutura do repositório (resumo)**

projeto-final-curso-i2a2/

├─ data/

│ ├─ bronze/            # Dados originais por fonte (ZIP/CSV/DBC)

│ ├─ silver/            # Parquets normalizados por fonte

│ └─ gold/              # Conjuntos finais (snis_rmb_indicadores_v2.*, gold_features_ano.*)

├─ scripts/             # ETLs (bronze_to_silver_*.py, silver_to_gold_features.py, etc.)

├─ notebooks/           # `analise_exploratoria_IA2A.ipynb`, `modelagem_IA2A.ipynb`

├─ dashboard/           # Exports Looker Studio + assets de apresentação

└─ docs/                # Este guia, roteiro, catálogo e dossiê final

**Convenção de camadas (sem jargão):**

- **Bronze:** dados “como vieram” das fontes (sem limpeza).  
    
- **Silver:** padronizados, com nomes e tipos coerentes (sem cálculos).  
    
- **Gold:** prontos para análise/modelagem (métricas agregadas, indicadores e features).  
    

## **4) Bases utilizadas e status atual**

### **4.1 SNIS/SINISA (serviços de água/esgoto) – Gold pronto**

- **Arquivo oficial:** `data/gold/snis_rmb_indicadores_v2.{csv,parquet}` (+ `*_raw` para auditoria se necessário).
- **Campos:** `cod_mun`, `municipio`, `ano`, índices de cobertura (`idx_atend_*`), coleta/tratamento, perdas (`idx_perdas_*`), hidrometração, tarifas e despesas por m³.
- **Uso:** base de cobertura/eficiência, alimenta diretamente o script `silver_to_gold_features.py` e os notebooks.

### **4.2 SISAGUA (qualidade da água) – Silver consolidado**

- **Bronze:** `data/bronze/sisagua/controle_mensal_parametros_basicos_20XX_csv.zip` (somente CSV).
- **Silver:** `python scripts/bronze_to_silver_sisagua_parquet.py --input-dir data/bronze/sisagua --out-dir data/silver/sisagua` (já executado). Particiona por ano/mês/UF.
- **Derivados:** o script `silver_to_gold_features.py` agrega diretamente do Silver (não há arquivo `gold_qualidade_agua.csv` separado). KPIs finais: `%_amostras_conformes` global e por parâmetro, `percentil95_turbidez`, etc.
- **Uso:** explica risco sanitário e compõe os painéis de qualidade.

### **4.3 INMET (clima) – Silver consolidado**

- **Bronze:** `data/bronze/inmet/<ano>/INMET_N_PA_*.CSV` (estações A201, A202, A227).
- **Silver:** `python scripts/inmet_to_parquet.py --input-dir data/bronze/inmet --output-dir data/silver/inmet` (já rodado). Normaliza cabeçalhos, datas e unidades.
- **Derivados:** agregações anuais (`chuva_total_mm`, `dias_calor_extremo`, `temp_media_c`) calculadas dentro do `silver_to_gold_features.py` e replicadas aos municípios mapeados.

### **4.4 SIH/DATASUS (internações) – Silver consolidado**

- **Bronze:** `data/bronze/sih/RDPAyymm.dbc` (2018–2025) + CSV intermediários em `data/bronze/sih/csv/`.
- **Silver:** pipeline `dbc_to_csv.py` ➜ `bronze_to_silver_sih_parquet.py` já executado, gerando partições `data/silver/sih/ano=YYYY/mes=MM/` com colunas `internacoes_total`, `internacoes_hidricas`, `valor_total`, etc.
- **Derivados:** taxas por 10 mil habitantes (`internacoes_total_10k`, `internacoes_hidricas_10k`) são calculadas ao gerar o Gold.

### **4.5 IBGE/SIDRA 6579 (população) – Silver pronto**

- **Arquivo:** `data/silver/ibge_populacao/populacao.parquet` com `cod_mun`, `municipio`, `ano`, `populacao`.
- **Uso:** denominador para normalizar internações e despesas per capita.

### **4.6 SIOPS (finanças saúde) – Silver pronto**

- **Arquivo:** `data/silver/siops/indicadores.parquet` (saída de `bronze_to_silver_siops_parquet.py`).
- **Campos principais:** `despesa_saude_pc`, `%_receita_propria_saude`, `%_transferencias_saude`, `gasto_total_saude` (quando existir).
- **Uso:** compõe o eixo financeiro no Gold e no dashboard.
    

## **5) O que manter em /data (checklist final)**

**Bronze (dados crus):**

- `data/bronze/sisagua/controle_mensal_parametros_basicos_20XX_csv.zip` (somente CSV).  
- `data/bronze/sih/RDPAyymm.dbc` + subpasta `csv/` com conversões recentes.  
- `data/bronze/ibge/sidra6579_pop_YYYY.csv` (2018–2025).  
- `data/bronze/inmet/<ano>/INMET_N_PA_*` apenas para estações A201/A202/A227.  
- `data/bronze/siops/siops_indicadores_rmb_2018_2025.csv` (ou equivalente).  

**Silver (Parquets prontos):** `data/silver/{sisagua,inmet,sih,siops,ibge_populacao}` – manter somente últimos recálculos.

**Gold:**

- `data/gold/snis_rmb_indicadores_v2.{csv,parquet}` (com versão `_raw` opcional para auditoria).  
- `data/gold/gold_features_ano.{csv,parquet}` (fonte dos notebooks e dashboard).  

**Pode arquivar/remover:** JSON/XML do SISAGUA, estações INMET fora do PA, DBC anteriores a 2018 e quaisquer intermediários obsoletos após validar o Gold.
    

## **6) Passo a passo operacional (vivemos nele)**

1. **Ativar ambiente** e instalar dependências (`python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`).
2. **Checar Bronze**: se novas coletas chegaram, colocar nas pastas corretas e registrar no `relato_coleta_tratamento.md`.
3. **Reprocessar Silver necessário** usando os scripts `bronze_to_silver_*.py` (SISAGUA, INMET, SIH, SIOPS, IBGE). Pular fontes sem novidade.
4. **Gerar o Gold único** com `python scripts/silver_to_gold_features.py`. Isso cria/atualiza `data/gold/gold_features_ano.{csv,parquet}` e mantém `snis_rmb_indicadores_v2.*` como insumo.
5. **Validar saída** via snippet rápido:
   ```python
   import pandas as pd
   df = pd.read_csv("data/gold/gold_features_ano.csv")
   assert df["cod_mun"].nunique() == 6
   print(df.groupby("ano")["pct_conformes_global"].describe())
   ```
6. **Distribuir outputs**: 
   - CSV `gold_features_ano` → Looker Studio / dashboard.
   - Parquet → notebooks `analise_exploratoria_IA2A` e `modelagem_IA2A`.
   - Atualizar `dashboard/material_para_dashboard/` com exports mais recentes.
        

## **7) Roteiro dos notebooks (o que já está pronto)**

### **Notebook – `analise_exploratoria_IA2A.ipynb`**

- **Entrada:** `data/gold/gold_features_ano.parquet` + `data/gold/snis_rmb_indicadores_v2.csv` para detalhes de serviço.
- **Escopo:**
  - Séries anuais por município (cobertura, perdas, conformidade, clima, internações).
  - Correlações e matrizes de dispersão relacionando serviço/qualidade × saúde.
  - Painéis rápidos de “top não conformidades” e “anotações para storytelling”.
- **Saídas:** tabelas/figuras exportadas para `dashboard/material_para_dashboard/` e para `docs/resumo_insights.md`.

### **Notebook – `modelagem_IA2A.ipynb`**

- **Entrada:** `data/gold/gold_features_ano.parquet` (mesma versão usada no dashboard).
- **Tarefas implementadas:**
  - Regressão para `internacoes_total_10k` com Linear Regression, Lasso e RandomForestRegressor.
  - Validação cruzada com MAE, RMSE, R² e comparação entre municípios.
  - Importância de variáveis (Permutation Importance) + explicações qualitativas para briefing.
- **Backlog opcional:** teste de classificação binária (flag de não conformidade) e SHAP para narrativa.

> _Boas práticas:_ sempre limpar o kernel antes de exportar, parametrizar caminhos usando `PATH_DATA = Path("data")` e enviar figuras ao painel/dossiê.
        

## **8) Dashboard (Looker Studio) – estrutura proposta**

**Página 1 – Visão Geral (RMB)**

- KPIs topo:  
    - **Cobertura água (%)**, **Coleta esgoto (%)**, **Tratamento esgoto (%)**,  
        
    - **Perdas na distribuição (%)**, **% amostras conformes**,  
        
    - **Internações por 10k**, **Despesa saúde per capita**, **Chuva anual (mm)**.  
        
- Mapa/Ranqueamento (por município) com **semaforização**.  
    
- Séries anuais 2018–2025 (linhas).  
    

**Página 2 – Município (drill-down)**

- Cartões por eixo: Serviço, Qualidade, Saúde, Clima, Finanças.  
    
- Barras de “principais não conformidades” (SISAGUA).  
    
- Painel de explicabilidade (importância de variáveis do modelo).  
    

**Página 3 – Prioridades & Simulação**

- Tabela de **priorização de investimentos** (ex.: top-3 ações por município).  
    
- Mini “What-if” (sliders simples) mostrando efeito esperado em **internações**.  
    

**Fonte dos dados do dashboard:** usar somente `data/gold/gold_features_ano.csv` como base principal e `data/gold/snis_rmb_indicadores_v2.csv` para detalhar indicadores de serviço quando precisar de mais granularidade. Não há outros arquivos gold paralelos.
    

## **9) Encerramento da preparação (lista objetiva)**

- SNIS/SINISA validado → `data/gold/snis_rmb_indicadores_v2.*`.
- Silver das demais fontes (`sisagua`, `inmet`, `sih`, `siops`, `ibge_populacao`) regenerado quando chega dado novo.
- `python scripts/silver_to_gold_features.py` rodado e auditado → `data/gold/gold_features_ano.{csv,parquet}`.
- Notebooks `analise_exploratoria_IA2A` e `modelagem_IA2A` executados com a mesma versão do Gold (limpar kernel antes de exportar).
- Dashboard Looker Studio conectado ao CSV atualizado e exports arquivados em `dashboard/`.
- /data organizado conforme checklist e documentação deste guia salva em `docs/`.
    

## **10) Dicionário (resumo dos principais campos “Gold”)**

| **Campo** | **Descrição** | **Observação** |
| --- | --- | --- |
| cod_mun | Código IBGE do município | Chave de junção |
| --- | --- | --- |
| municipio | Nome do município | Padronizado |
| --- | --- | --- |
| ano | Ano de referência | 2018–2025 |
| --- | --- | --- |
| idx_atend_agua_total | % população total atendida com água | SNIS |
| --- | --- | --- |
| idx_coleta_esgoto | % população com coleta | SNIS |
| --- | --- | --- |
| idx_tratamento_esgoto | % esgoto coletado que é tratado | SNIS |
| --- | --- | --- |
| idx_perdas_distribuicao | % perdas na distribuição | SNIS |
| --- | --- | --- |
| idx_hidrometracao | % ligações com hidrômetro | SNIS |
| --- | --- | --- |
| pct_conformes_global | % de amostras conformes (global) | Calculado a partir do Silver SISAGUA ao gerar o Gold |
| --- | --- | --- |
| percentil95_turbidez, percentil95_cloro_residual_livre | Percentil 95 dos parâmetros críticos | SISAGUA (Gold) |
| --- | --- | --- |
| chuva_total_mm, dias_calor_extremo | Clima agregado anual | INMET (Gold) |
| --- | --- | --- |
| despesa_saude_pc | R$ per capita em saúde | SIOPS |
| --- | --- | --- |
| internacoes_total_10k | Internações por 10 mil hab. | SIH + IBGE (alvo y) |
| --- | --- | --- |

**Importante:** manter variáveis em **escala coerente** (percentuais 0–100; monetários em R$; contagens absolutas). A conferência de escala dos índices **já foi corrigida** no snis_rmb_indicadores_v2.csv.

## **11) Entrega mínima para o time começar já**

1. Rodar `scripts/silver_to_gold_features.py` com os Silver atualizados e compartilhar `data/gold/gold_features_ano.csv` + `snis_rmb_indicadores_v2.csv` no Drive.
2. Validar que existem **6 municípios × anos** sem buracos e que percentuais permanecem na escala 0–100.
3. Atualizar README/guia (este arquivo) com a data da rodada e linkar no canal com o time.
4. Congelar o schema do Gold (não renomear colunas) até a banca/finalização do dashboard.
5. Distribuição rápida: `analise_exploratoria_IA2A.ipynb` roda com a nova versão para extrair insights; `modelagem_IA2A.ipynb` recalcula métricas; dashboard consome o CSV recém-publicado.
    

## **12) Observações finais**

- Você já fez o mais difícil: **coleta, padronização e conferência**.  
    
- A partir daqui, o foco é **consistência** (mesmos nomes, mesmas escalas) e **clareza** na comunicação (painéis e explicações simples).  
    
- Qualquer ajuste de última hora, priorizar **correção de escala e chaves**; depois, gráficos/modelos.