# Dashboard de Anomalias no Teste de Gravação de Setupbox

Projeto da Tarefa Assíncrona 01 da disciplina Técnicas de Hiperautomação.

## Objetivo

Construir um dashboard em código para analisar anomalias no processo de gravação de setupboxes a partir do arquivo `recording_test_setupbox.xlsx`.

O dashboard deve carregar os dados, apresentar KPIs e visualizações de processo, permitir auditoria por filtros e exportar um relatório com os principais achados.

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

## Estrutura Prevista Do Dashboard

- Visão Geral
- Pareto de Defeitos
- Jig x Etapa
- Falhas no Tempo
- Cycle Time
- Yield, Rework e Scrap
- Auditoria
- Processo BPMN/PDD
- Relatório

## Integrantes

- Marcelo Vitor Duarte Uchoa
- Rebecca Souza Xavier
- Gabriel Fernandes Gouvea de Sá
