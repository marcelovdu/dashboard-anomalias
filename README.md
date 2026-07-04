# Monitor de Anomalias no Teste de Gravação de Setupbox

Projeto desenvolvido para a Tarefa Assíncrona 02 da disciplina **Técnicas de Hiperautomação**.

O sistema combina um dashboard interativo em **Streamlit** com um **monitor automático de anomalias**. O dashboard apoia a análise visual do processo de gravação de setupboxes, enquanto o monitor processa logs em janelas móveis, detecta anomalias, emite alertas estruturados, registra auditoria e separa casos para revisão humana.

## Integrantes da Equipe

- Marcelo Vitor Duarte Uchoa
- Rebecca Souza Xavier
- Gabriel Fernandes Gouvea de Sá

## Objetivo

Construir um monitor capaz de analisar o processo de gravação de setupboxes a partir do arquivo `recording_test_setupbox.xlsx` ou de uma pasta de logs equivalentes.

A aplicação permite:

- carregar automaticamente a base de dados;
- visualizar indicadores (KPIs) do processo no dashboard;
- identificar anomalias e defeitos recorrentes em janelas móveis;
- classificar severidade e sugerir ações;
- gerar alertas em CSV;
- registrar trilha de auditoria;
- encaminhar casos ambíguos ou severos para revisão humana (HITL);
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

## Como Executar o Dashboard

1. Crie e ative um ambiente virtual, se ainda não existir:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Execute o dashboard:

```bash
python -m streamlit run app.py
```

No Linux, se o comando `python` não existir, use:

```bash
python3 -m streamlit run app.py
```


> No Windows, se o comando `streamlit run app.py` não for reconhecido pelo PowerShell,
> use `python -m streamlit run app.py`. Isso executa o Streamlit pelo Python em que o
> pacote foi instalado, sem depender do executável `streamlit` estar no PATH.

4. No navegador, use os filtros laterais para explorar os dados.

## Como Executar o Monitor

Execute o monitor sobre a planilha padrão:

```bash
python monitor.py --input recording_test_setupbox.xlsx --output saida_monitor
```

Ou, usando diretamente a venv do projeto:

```bash
.venv/bin/python monitor.py --input recording_test_setupbox.xlsx --output saida_monitor
```

Com uma pasta de logs:

```bash
python monitor.py --input dados_logs/entrada --output saida_monitor
```

Parâmetros úteis:

```bash
python monitor.py --input recording_test_setupbox.xlsx --output saida_monitor --window-minutes 60 --step-minutes 15 --baseline-hours 12 --min-consecutive 2
```

Com gabarito de incidentes para avaliação:

```bash
python monitor.py --input dados_logs/entrada --gabarito dados_logs/gabarito_incidentes.csv --output saida_monitor
```

Saídas geradas em `saida_monitor/`:

- `alertas.csv`: alertas estruturados;
- `auditoria.csv`: trilha de janelas processadas;
- `revisao_humana.csv`: fila HITL;
- `avaliacao.csv`: precisão, recall, latência e falso alarme quando houver gabarito;
- `pareamentos_gabarito.csv`: correspondência entre alertas e incidentes;
- `relatorio_monitor.html`: relatório periódico do monitor.

## Arquivos Esperados

- `recording_test_setupbox.xlsx`: base de dados com as abas `recordings`, `line_stops` e `data_dictionary`.
- `app.py`: aplicação Streamlit.
- `monitor.py`: monitor automático de anomalias.
- `src/`: funções de carga, tratamento, métricas, regras, alertas, avaliação e relatórios.
- `assets/`: imagens ou arquivos auxiliares do BPMN/PDD.
- `docs/`: BPMN to-be, PDD do monitor e orientação de avaliação.
- `relatorios/`: relatórios exportados.
- `saida_monitor/`: arquivos gerados pelo monitor.

## Estrutura do Dashboard

O dashboard é composto pelas seguintes seções:

- Visão Geral
- Indicadores (KPIs)
- Pareto de Defeitos
- Jig x Etapa
- Falhas ao Longo do Tempo
- Cycle Time
- Yield, Rework e Scrap
- Auditoria
- Processo (BPMN/PDD)
- Exportação de Relatórios

## Estrutura do Projeto

```text
Dashboard/
├── app.py
├── monitor.py
├── README.md
├── requirements.txt
├── assets/
├── docs/
├── relatorios/
├── saida_monitor/
└── src/
    ├── alertas.py
    ├── avaliacao.py
    ├── carregar_dados.py
    ├── metricas.py
    ├── monitoramento.py
    ├── processo.py
    ├── regras.py
    ├── relatorio.py
    ├── relatorio_monitor.py
    └── tratamento.py
```

## Funcionalidades

- Dashboard interativo com Streamlit
- Monitor automático em janelas móveis
- Alertas estruturados em CSV
- HITL para revisão humana
- Auditoria de janelas e decisões
- Filtros dinâmicos
- Indicadores de qualidade
- Análise de defeitos
- Visualização do processo
- Geração de relatório em HTML/PDF
- Auditoria dos registros
