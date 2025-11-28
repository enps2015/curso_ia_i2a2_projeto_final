# Relato da Etapa de Coleta e Tratamento de Dados

> Documento complementar aos guias técnicos. Registra as principais decisões, obstáculos e lições aprendidas durante a preparação das camadas Bronze → Silver → Gold do TCC "Água, Saneamento e Saúde na RMB".

## 1. Resumo da etapa

- **Objetivo:** consolidar fontes públicas de saneamento, qualidade da água, clima, saúde e finanças para os seis municípios da RMB (2018–2025), entregando camadas Silver e Gold prontas para análises, modelagens e dashboards.
- **Autores:** equipe de dados do TCC (coleta, limpeza, normalização e estruturação).
- **Situação final:** repositório organizado em camadas `data/bronze`, `data/silver` e `data/gold`, com scripts ajustados para os novos caminhos e documentação atualizada.

## 2. Obstáculos encontrados e soluções adotadas

### 2.1 Divergências de formatos e colunas
- **SNIS/SINISA:** algumas planilhas traziam percentuais acima de 100% e códigos IBGE com 6 dígitos.
  - *Solução:* script `fix_snis_csv.py` normalizou percentuais, padronizou códigos para 7 dígitos e gerou a versão `snis_rmb_indicadores_v2` em `data/gold/`.
- **SISAGUA:** parâmetros variavam de nome (ex.: `cloro_residual_livre_mg_l` vs `cloro_residual_livre`).
  - *Solução:* o ETL Silver (`bronze_to_silver_sisagua_parquet.py`) inclui dicionário de aliases, unifica nomes e classifica campos conforme a Portaria 888/2021.

### 2.2 Falhas e lacunas nas fontes
- **SIDRA/IBGE:** arquivos 2022 e 2023 retornaram vazios em algumas consultas.
  - *Solução:* o conversor ignora planilhas sem dados (logando aviso) e prossegue com os anos válidos, evitando travar o pipeline.
- **INMET:** estações extras e cabeçalhos inconsistentes por ano.
  - *Solução:* curadoria manual manteve apenas as estações PA A201, A202 e A227. O script `inmet_to_parquet.py` padroniza colunas e converte datas/horas.

### 2.3 Consolidação de chaves
- **Códigos IBGE mistos (6/7 dígitos)** e nomes com acentos.
  - *Solução:* todos os scripts Silver e Gold utilizam `config/rmb_municipios.csv` como fonte única, com mapeamentos para 6 e 7 dígitos e nomes normalizados em caixa alta.

### 2.4 Estrutura legada do projeto
- Diretórios e scripts apontavam para `data/curated/` e arquivos avulsos.
  - *Solução:* reorganização completa em Bronze/Silver/Gold, ajuste de scripts (`bronze_to_silver_*`, `silver_to_gold_features.py`, etc.) e atualização do `README.md` e demais guias.

## 3. Status final por camada

| Camada | Diretórios principais | Conteúdo atual | Observações |
| ------ | -------------------- | -------------- | ----------- |
| **Bronze** | `data/bronze/ibge`, `data/bronze/inmet`, `data/bronze/sih` (+`csv/`), `data/bronze/sisagua`, `data/bronze/siops`, `data/bronze/snis` | Fontes brutas conforme download original | Manter apenas anos úteis; arquivos auxiliares vão para `data/_archive`. |
| **Silver** | `data/silver/sih`, `data/silver/sisagua`, `data/silver/siops`, `data/silver/inmet`, `data/silver/ibge_populacao` | Parquets padronizados com chaves e tipos coerentes | Reconstruídos via scripts `bronze_to_silver_*`. |
| **Gold** | `data/gold/` | `snis_rmb_indicadores_v2.*`, `gold_qualidade_agua.*`, `gold_features_ano.*` (entre outros derivados) | Base oficial para notebooks, modelos e dashboards. |
| **Notebooks** | `notebooks/` | Pasta criada para EDA/modelagem (a preencher pelo time) | Sem conteúdo ainda (aguarda próximos ciclos). |
| **Dashboards** | `dashboard/` | Pasta nova para exportações (PDF, PNG, links) | Usar quando o Looker Studio for atualizado. |

## 4. Riscos e pendências mapeados

1. **População 2022–2023:** ausência de dados SIDRA pode impactar normalizações per capita; documentar qualquer interpolação futura.
2. **SISAGUA 2024–2025:** verificar se novos parâmetros surgem e atualizar o dicionário de aliases antes de gerar Gold mensal.
3. **Modelagem climática:** associações estação→município usam proxys (ex.: A227 para Barcarena); revisar premissas se novos dados aparecerem.
4. **Documentos binários (`.docx/.pdf`):** ainda citam estrutura antiga; precisam ser atualizados manualmente para evitar inconsistências.

## 5. Lições aprendidas

- **Padronização antecipada poupa retrabalho:** manter `config/rmb_municipios.csv` como fonte única simplificou todos os joins.
- **Registrar correções em scripts dedicados** (ex.: SNIS v2) facilita reproduzir os resultados e entender ajustes.
- **Estrutura Bronze/Silver/Gold ajuda o time inteiro:** clareza para quem modela, cria dashboards e audita os dados.
- **Logs e avisos nos scripts** economizam depuração (ex.: avisos de CSV vazio no IBGE, warnings no SISAGUA).

## 6. Próximos passos recomendados

1. **Modelagem/EDA:** colegas devem criar notebooks em `notebooks/`, seguindo o roteiro `docs/roteiro_analises_modelagem_dashboard.md`.
2. **Dashboards:** ao finalizar views no Looker Studio, exportar evidências para `dashboard/`.
3. **Documentação complementar:** atualizar arquivos `.docx/.pdf` com a nova estrutura e registrar eventuais ajustes adicionais.
4. **Validação cruzada:** executar um *dry run* dos scripts críticos antes das análises para garantir que nenhum caminho antigo voltou a aparecer.

---

> Documento produzido em 3 de novembro de 2025. Manter como registro histórico desta fase da preparação de dados.
