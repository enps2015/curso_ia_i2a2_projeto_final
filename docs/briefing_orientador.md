# Briefing de mentoria – traduzindo as análises para o time

Professor, seguem os principais pontos para garantirmos que todo o grupo esteja na mesma página antes da reunião:

## 1. Como estruturamos o diagnóstico

1. **Notebook exploratório = exame completo**  
   - Consolidamos os 8 municípios da RMB (2018–2025) com todos os indicadores de saneamento, qualidade de água, clima e finanças.  
   - Geramos dois "exames laboratoriais" que alimentam diretamente o dashboard: `painel_prioridade.csv` (ranking atual e score de risco) e `ods_tracker.csv` (checagem anual das metas ODS 6/3/11).  
   - As cinco perguntas de negócio (melhor ação, retorno por município, impacto da chuva, ranking 12 meses e status ODS) já podem ser respondidas apenas com essa base.

2. **Notebook de modelagem = simulador de médico**  
   - Pegamos o mesmo dataset preparado no EDA e treinamos três “médicos virtuais” (Regressão Linear, Lasso e RandomForest).  
   - O RandomForest foi escolhido porque lida melhor com a bagunça dos dados reais: ele junta várias árvores de decisão votando juntas, então captura relações do tipo “se a cobertura cai e a chuva aumenta, as internações disparam”.  
   - Exportamos quatro arquivos extras para o Looker: métricas do modelo, importâncias, previsões históricas e cenários de elasticidade.

## 2. Conceitos explicados sem jargão

- **Holdout (ano de teste)**: escondemos o ano de 2025 do treino para ver se o modelo realmente aprendeu ou se só decorou o passado. É a “prova final” do aluno.  
- **MAE vs. R²**: o MAE (~4 internações por 10k hab.) mostra o erro médio absoluto — ainda aceitável para comparações relativas. O R² ficou negativo porque 2025 é bastante diferente dos anos anteriores e nossa amostra é pequena (64 combinações município/ano). Em termos médicos, o paciente apresentou sintomas novos e o histórico era curto — o modelo precisa de mais consultas para ter segurança plena.  
- **Interpretação prática**: usamos o modelo como bússola (direção e sensibilidade a mudanças) e não como bola de cristal. Isso é suficiente para guiar intervenções e montar os painéis “what-if”.

## 3. Principais insights para levar à reunião

- **Drivers confirmados**: déficits de saneamento (tratamento, cobertura, qualidade) e clima (chuva/umidade) explicam a maioria das oscilações. Investimentos em saúde aparecem como fator protetor — municípios que aumentam o percentual dedicado a investimentos tendem a reduzir a taxa.  
- **Ranking e metas**: Ananindeua, Belém e Santa Izabel seguem críticos em 2025; tratamento e qualidade da água permanecem abaixo das metas ODS em todos os anos.  
- **Elasticidades**: um aumento de +5 p.p. em cobertura/tratamento/qualidade reduz de forma consistente a taxa prevista (–0,11 a –0,19 por 10k). Esse dado alimenta os cards “quanto precisamos mexer para reduzir X internações” no dashboard.

## 4. Próximos passos sugeridos

1. Atualizar as fontes do Looker com os CSVs já gerados.  
2. Usar este documento + `docs/resumo_insights.md` como script na reunião com o senhor.  
3. Se precisarmos melhorar o R², propor ações futuras (mais anos, variáveis defasadas adicionais, tuning do RandomForest).

Assim todo o grupo, inclusive quem está começando em IA, consegue defender as escolhas técnicas e mostrar segurança diante das perguntas. Obrigado pelo acompanhamento — seguimos afinando conforme seu feedback.
