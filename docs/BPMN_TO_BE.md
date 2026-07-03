# BPMN To-Be - Monitor de Anomalias

Este fluxo representa o processo proposto para a Tarefa 02: o log deixa de ser analisado apenas no fim do período e passa a ser monitorado em janelas, com alerta, revisão humana e auditoria.

```mermaid
flowchart TD
    A[Início da janela de monitoramento] --> B[Ingerir logs em ordem cronológica]
    B --> C[Tratar dados e atualizar histórico]
    C --> D[Calcular métricas da janela móvel]
    D --> E[Aplicar regras de anomalia]
    E --> F{Existe candidato a anomalia?}
    F -- Não --> G[Registrar janela sem alerta na auditoria]
    G --> H{Há nova janela?}
    F -- Sim --> I{É sistemático ou crítico?}
    I -- Não / ambíguo --> J[Enviar para revisão humana HITL]
    J --> K[Registrar pendência e evidência]
    I -- Sim --> L[Classificar severidade]
    L --> M[Selecionar ação sugerida pelo runbook]
    M --> N[Emitir alerta estruturado]
    N --> O{Severidade alta ou crítica?}
    O -- Sim --> J
    O -- Não --> P[Registrar alerta e ação na auditoria]
    K --> Q[Humano aprova, rejeita ou ajusta ação]
    Q --> R[Registrar decisão humana]
    R --> P
    P --> S[Atualizar relatório periódico]
    S --> H
    H -- Sim --> A
    H -- Não --> T[Encerrar execução do monitor]
```

## Pontos de Decisão

- `Existe candidato a anomalia?`: verifica se alguma regra atingiu volume, taxa ou desvio acima do limiar.
- `É sistemático ou crítico?`: confirma se a regra apareceu em janelas consecutivas ou se é uma regra crítica, como MAC duplicado.
- `Severidade alta ou crítica?`: envia casos de maior risco para revisão humana obrigatória.

## Trilhas de Auditoria

- Toda janela processada gera uma linha em `saida_monitor/auditoria.csv`.
- Todo alerta gera uma linha em `saida_monitor/alertas.csv`.
- Todo caso com HITL gera uma linha em `saida_monitor/revisao_humana.csv`.
- A avaliação contra gabarito, quando fornecida, gera `saida_monitor/avaliacao.csv`.
