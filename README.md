# Dashboard de Anomalias no Teste de Gravação de Setupbox

Projeto desenvolvido para a Tarefa Assíncrona 01 da disciplina **Técnicas de Hiperautomação**. 

O sistema consiste em um dashboard interativo desenvolvido com **Python** e **Streamlit** para analisar anomalias no processo de gravação de setupboxes, permitindo acompanhar indicadores de desempenho, identificar falhas recorrentes e gerar relatórios para apoio à tomada de decisão.

## Integrantes da Equipe

- Marcelo Vitor Duarte Uchoa
- Rebecca Souza Xavier
- Gabriel Fernandes Gouvea de Sá

## Objetivo

Construir um dashboard capaz de analisar o processo de gravação de setupboxes a partir do arquivo `recording_test_setupbox.xlsx`.

A aplicação permite:

- carregar automaticamente a base de dados;
- visualizar indicadores (KPIs) do processo;
- identificar anomalias e defeitos recorrentes;
- aplicar filtros para auditoria;
- visualizar métricas de qualidade e produtividade;
- exportar relatórios com os principais resultados.


## Tecnologias Utilizadas

- Python 3
- Streamlit
- Pandas
- Plotly
- OpenPyXL
- HTML/PDF para geração de relatórios


## Como Executar

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

2. Execute o dashboard:

```bash
streamlit run app.py
```

3. No navegador, use os filtros laterais para explorar os dados.

## Arquivos Esperados

- `recording_test_setupbox.xlsx`: base de dados com as abas `recordings`, `line_stops` e `data_dictionary`.
- `app.py`: aplicação Streamlit.
- `src/`: funções de carga, tratamento e métricas.
- `assets/`: imagens ou arquivos auxiliares do BPMN/PDD.
- `relatorios/`: relatórios exportados.

## Estrutura do Dashboard

O dashboard é composto pelas seguintes seções:

- Visão Geral
- Indicadores (KPIs)
- Pareto de Defeitos
- Jig × Etapa
- Falhas ao Longo do Tempo
- Cycle Time
- Yield, Rework e Scrap
- Auditoria
- Processo (BPMN/PDD)
- Exportação de Relatórios

---

## Estrutura do Projeto

```text
Dashboard/
├── app.py
├── README.md
├── requirements.txt
├── assets/
├── relatorios/
└── src/
    ├── carregar_dados.py
    ├── metricas.py
    ├── processo.py
    ├── relatorio.py
    └── tratamento.py
```

## Funcionalidades

- Dashboard interativo com Streamlit
- Filtros dinâmicos
- Indicadores de qualidade
- Análise de defeitos
- Visualização do processo
- Geração de relatório em HTML/PDF
- Auditoria dos registros

