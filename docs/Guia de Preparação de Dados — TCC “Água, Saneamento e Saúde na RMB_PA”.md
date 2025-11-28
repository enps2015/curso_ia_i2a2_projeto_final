# **Guia de Preparação de Dados - TCC "Água, Saneamento e Saúde na RMB/PA"**

**Propósito deste guia  
**Colocar qualquer pessoa (humana ou IA) "no meio do bonde" com contexto total do projeto, o **porquê**, **o que** já fizemos e **como** finalizar a etapa de **preparação de dados** até deixar tudo pronto para **análises, modelagem e dashboards**.

## **1) Ideia do TCC (o que estamos construindo)**

**Tema:** Priorização de investimentos em água e esgoto na **Região Metropolitana de Belém (RMB/PA)**, usando **dados públicos** e **IA** para relacionar **saneamento (acesso/qualidade)**, **clima** e **efeitos em saúde**.

**Pergunta-guia:** Onde investir primeiro (por município/bairro) para **maximizar impacto** em **saúde pública**, **eficiência operacional** e **equidade**?

**MVP (entregáveis):**

- **Notebook** com análises + **modelos** de priorização (regras + ML simples)  

- **Dashboard** profissional (Looker Studio) com KPIs e narrativas  

- **Pacote de dados** prontos (Bronze/Silver/Gold) e dicionários  

**ODS (rastreabilidade):**

- **ODS 6** (Água potável e Saneamento) - 6.1, 6.2, 6.3  

- **ODS 3** (Saúde e Bem-Estar) - 3.3, 3.9  

- **ODS 11** (Cidades Sustentáveis) - 11.6  

- **ODS 13** (Ação Climática) - 13.1  

## **2) Escopo técnico (alto nível)**

**Unidades de análise:** município/ano (e mês quando possível).  
**Municípios RMB:** Belém, Ananindeua, Marituba, Benevides, Santa Bárbara do Pará, Santa Izabel do Pará.

**Arquitetura de dados (camadas):**

- **Bronze:** dados brutos/baixados (CSV/ZIP/DBC/XLSX), sem padronização  

- **Silver:** padronizados e **parquet particionado**, chaves (cod_mun, ano, mes)  

- **Gold:** tabelas prontas para o **dashboard** e **modelos** (KPIs finais)  

**Chaves & padrões:**

- cod_mun (IBGE, **7 dígitos**)  

- municipio (MAIÚSCULO, **sem acento**)  

- ano (YYYY) | mes (1-12)  

- Tempo: UTC-3; strings BR ➜ número (trocar , por .).  

## **3) Fontes de dados (o que cada uma entrega)**

| **Fonte** | **Para quê?** | **Período** | **Onde está (pasta)** | **Status** |
| --- | --- | --- | --- | --- |
| **SNIS/SINISA (indicadores água/esgoto)** | Cobertura de água/esgoto, perdas, hidrometração, tarifas | 2018-2023 | data/gold/snis_rmb_indicadores_v2.* | **Gold pronto** (v2 validado) |
| --- | --- | --- | --- | --- |
| **SISAGUA (qualidade da água)** | Parâmetros físico-químicos e microbiológicos | 2018-2025 | data/silver/sisagua/ano=YYYY/mes=MM/*.parquet | **Silver consolidado** (rerodar script só se baixar novo ZIP) |
| --- | --- | --- | --- | --- |
| **INMET (clima)** | Temperatura, umidade, chuva | 2018-2025 | data/silver/inmet/ano=YYYY/estacao=.../*.parquet | **Silver consolidado** (estações A201/A202/A227) |
| --- | --- | --- | --- | --- |
| **IBGE (SIDRA 6579)** | População total/urbana (denominadores) | 2018-2025 | data/silver/ibge_populacao/populacao.parquet | **Silver pronto** (usado para normalizar) |
| --- | --- | --- | --- | --- |
| **SIH (Datasus)** | Internações (CID hídrico), proxy de agravos | 2018-2025 | data/silver/sih/ano=YYYY/mes=MM/*.parquet | **Silver agregado** (DBC→CSV→Parquet já aplicado) |
| --- | --- | --- | --- | --- |
| **SIOPS** | Despesa em saúde (contexto fiscal) | 2018-2024 | data/silver/siops/indicadores.parquet | **Silver pronto** (indicadores padronizados) |
| --- | --- | --- | --- | --- |

## **4) O que já foi feito (essencial)**

- **SNIS/SINISA 2018-2023**: ETL, unificação e **correção de percentuais** ➜ `data/gold/snis_rmb_indicadores_v2.{csv,parquet}` prontos para uso.  
    Colunas-chave (disponíveis): `cod_mun`, `municipio`, `ano`, `idx_atend_agua_total`, `idx_atend_agua_urbano`, `idx_coleta_esgoto`, `idx_tratamento_esgoto`, `idx_esgoto_tratado_ref_agua`, `idx_hidrometracao`, `idx_perdas_distribuicao`, `idx_perdas_lineares`, `idx_perdas_por_ligacao`, `tarifa_media_praticada`, `tarifa_media_agua`, `tarifa_media_esgoto`, `despesa_total_m3`, `despesa_exploracao_m3`.  

- **SISAGUA 2018-2025**: CSVs por ano tratados, padronizados e convertidos para Parquet particionado (`data/silver/sisagua/ano=YYYY/mes=MM/UF=PA/...`).  

- **INMET**: anos 2018-2025 normalizados em Parquet (`data/silver/inmet/ano=YYYY/estacao=...`) mantendo as estações A201 (Belém), A202 (Castanhal/Santa Izabel/Santa Bárbara) e A227 (proxy Barcarena).  

- **IBGE (SIDRA 6579)**: populacional consolidado em `data/silver/ibge_populacao/populacao.parquet` com `cod_mun` padronizado.  

- **SIH (RDPA yymm)**: DBC ➜ CSV ➜ Parquet aplicados, agregando internações hídricas e totais por município/mês (`data/silver/sih`).  

- **SIOPS**: indicadores financeiros limpos em `data/silver/siops/indicadores.parquet`.  

## **5) Como atualizar (quando chegar dado novo)**

### **5.1 Bronze → Silver (scripts já disponíveis)**

Os diretórios `data/silver/*` já estão populados. Rode novamente **somente** se algum Bronze for atualizado:

- **SISAGUA**: `python scripts/bronze_to_silver_sisagua_parquet.py --input-dir data/bronze/sisagua --out-dir data/silver/sisagua`
- **INMET**: `python scripts/inmet_to_parquet.py --input-dir data/bronze/inmet --output-dir data/silver/inmet`
- **IBGE/SIDRA**: `python scripts/bronze_to_silver_ibge_pop_parquet.py --input-dir data/bronze/ibge --output-file data/silver/ibge_populacao/populacao.parquet`
- **SIH**: 
    1. `python scripts/dbc_to_csv.py --src data/bronze/sih --dst data/bronze/sih/csv`
    2. `python scripts/bronze_to_silver_sih_parquet.py --csv-dir data/bronze/sih/csv --out-dir data/silver/sih`
- **SIOPS**: `python scripts/bronze_to_silver_siops_parquet.py --input data/bronze/siops/siops_indicadores_rmb_2018_2025.csv --out data/silver/siops/indicadores.parquet`

> _Dica_: manter somente os ZIP/DBC originais em Bronze e sobrescrever Silver; os scripts preservam partições por ano/mês.

### **5.2 Silver → Gold (dataset oficial)**

Após garantir que todos os Silver foram gerados/atualizados, execute:

```bash
python scripts/silver_to_gold_features.py \
    --out-parquet data/gold/gold_features_ano.parquet \
    --out-csv data/gold/gold_features_ano.csv
```

Esse passo:

- Lê `data/gold/snis_rmb_indicadores_v2.*` + todos os Silver.
- Calcula KPIs anuais de qualidade da água direto da camada Silver SISAGUA (não é necessário um arquivo `gold_qualidade_agua.csv` separado).
- Normaliza população e gera derivados como `internacoes_total_10k`, `pct_conformes_global` e `dias_calor_extremo` por município/ano.

Resultado final = `data/gold/gold_features_ano.{csv,parquet}`, fonte única para notebooks, modelos e dashboard.

## **6) Passo-a-passo (runbook atualizado)**

1. **Preparar ambiente**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
2. **Conferir Bronze**: valide se há novos arquivos em `data/bronze/<fonte>/`. Se nada mudou, siga para o passo 4.
3. **Regenerar Silver (quando necessário)**: use os comandos da seção 5.1 somente para as fontes atualizadas.
4. **Gerar o Gold anual**: `python scripts/silver_to_gold_features.py`. O script lê todas as fontes e escreve `data/gold/gold_features_ano.{csv,parquet}`.
5. **Smoke test** (garante integridade antes de rodar notebooks):
    ```python
    import pandas as pd

    df = pd.read_parquet("data/gold/gold_features_ano.parquet")
    print(df.groupby("municipio").size())
    assert df["cod_mun"].astype(str).str.len().eq(7).all()
    assert df[["pct_conformes_global", "idx_atend_agua_total"]].max().le(110).all()
    ```
6. **Exportar para dashboards/notebooks**: copie `data/gold/gold_features_ano.csv` (fonte Looker) e mantenha os Parquets para pipelines Python.

## **7) O que fica no diretório /data (para prosseguir)**

data/

├─ bronze/

│ ├─ ibge/ sidra6579_pop_2018.csv … sidra6579_pop_2025.csv

│ ├─ inmet/ <ano>/INMET_N_PA_\*.CSV (estações A201/A202/A227)

│ ├─ sih/ RDPA\*.dbc (2018-2025) e subpasta `csv/`

│ ├─ siops/ siops_indicadores_rmb_2018_2025.csv (ou equivalente)

│ └─ sisagua/ controle_mensal_parametros_basicos_20{18..25}_csv.zip

├─ silver/

│ ├─ ibge_populacao/populacao.parquet

│ ├─ inmet/estacao=.../ano=...

│ ├─ sih/ano=YYYY/mes=MM

│ ├─ siops/indicadores.parquet

│ └─ sisagua/ano=YYYY/mes=MM

└─ gold/

    ├─ snis_rmb_indicadores_v2.{csv,parquet}

    └─ gold_features_ano.{csv,parquet}

**Pode mover para data/\_archive/ ou excluir:  
**JSON/XML do SISAGUA, estações INMET não utilizadas, ZIPs do SNIS já processados.

## **8) Dicionário rápido (variáveis críticas)**

**SNIS/SINISA (v2):**

- idx_atend_agua_total, idx_atend_agua_urbano - % cobertura água  

- idx_coleta_esgoto, idx_tratamento_esgoto - % coleta/tratamento  

- idx_perdas_distribuicao, idx_perdas_lineares, idx_perdas_por_ligacao - perdas  

- idx_hidrometracao - % ligações com hidrômetro  

- tarifa_media_\*, despesa_\*\_m3 - R\$/m³  

**SISAGUA (Silver):**

- Parâmetros por **mês/município** (ex.: **Cloro Livre**, **Turbidez**, **Coliformes**, **E. coli**).  

- KPIs Gold: % amostras conformes por parâmetro e global.  

**INMET (Silver):**

- data, hora, chuva_mm, temp_c, umid_rel _(nomes padronizados pela conversão)_.  

**IBGE (Silver):**

- pop_total, pop_urbana.  

**SIH (Silver):**

- internacoes_total (mensal) e/ou taxa por 100k (com IBGE).  

**SIOPS (Silver):**

- despesa_saude_total, despesa_pc (R\$/hab).  

**gold_features_ano (Gold):**

- pct_conformes_global, pct_conformes_<parametro> (cloro, turbidez, pH, coliformes, E. coli).  
- chuva_total_mm, dias_calor_extremo, temp_media_c.  
- despesa_saude_pc, valor_medio_internacao, internacoes_total_10k, internacoes_hidricas_10k.  
- idx_perdas_*, idx_atend_agua_*, idx_coleta/tratamento, tarifa_media_*.  

## **9) KPIs e painéis (o que o dashboard vai exibir)**

- **Cobertura:** água total/urbana, coleta e tratamento de esgoto (%)  

- **Qualidade:** % amostras conformes (global e por parâmetro crítico)  

- **Operação:** perdas (distribuição/lineares/por ligação), hidrometração, tarifa média  

- **Saúde:** internações/100 mil (mensal/anual)  

- **Clima:** chuva anual/mensal (contexto de risco)  

- **Gasto:** despesa saúde per capita  

- **Prioridade:** ranking por score (regras claras e explicáveis)  

## **10) Checklist final para "entregar aos analistas"**

- `data/bronze/` contém somente fontes oficiais necessárias (ZIP/DBC originais).
- `data/silver/` atualizado para SISAGUA, INMET, SIH, SIOPS e IBGE (rodou scripts após qualquer mudança).
- `data/gold/snis_rmb_indicadores_v2.*` integra a camada de serviço já validada.
- `data/gold/gold_features_ano.{csv,parquet}` foi regenerado e validado pelo smoke test do passo 6.
- Dashboard/Looker atualizado apontando para a versão atual do CSV.
- Este guia salvo em `docs/` com data/autor da última revisão.

## **11) Fricções conhecidas & notas de operação**

- **Percentuais SNIS**: validação aplicada no v2; se surgir valor >100, marcar e revisar coluna de origem.  

- **SISAGUA**: nomes de parâmetros variam por ano; o script Silver **mapeia sinônimos**.  

- **INMET**: cabeçalhos mudam por estação/ano; conversor Silver padroniza.  

- **SIH**: escolha de CIDs de interesse (gastroenterites etc.) pode ser ajustada; começar por **total** mensal.  

- **Unidades**: padronizar tudo em SI e BRL; formatos de data/hora em UTC-3.  

### **Como usar este guia**

- Cole este arquivo como **docs/guia_preparacao.md** no projeto.  

- Use as seções 5-6 como **checklist/roteiro** no VS Code (Codex).  

- Se algo não bater, **anexe o log/erro** que eu te devolvo o patch do script.  

Vai dar bom. Você já fez o mais difícil: **coletar, entender e corrigir**. Agora é só **transformar para Silver** e **montar o Gold** que alimenta o dashboard.