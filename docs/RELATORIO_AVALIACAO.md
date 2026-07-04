# Relatório de Avaliação do Monitor

Este documento descreve como interpretar a avaliação gerada pelo monitor.

## Execução sem Gabarito

```bash
python monitor.py --input recording_test_setupbox.xlsx --output saida_monitor
```

Nesse modo, o monitor gera alertas e auditoria, mas as métricas de precisão, recall, latência e falso alarme ficam pendentes em `saida_monitor/avaliacao.csv`.

## Execução com Gabarito

```bash
python monitor.py --input dados_logs/entrada --gabarito dados_logs/gabarito_incidentes.csv --output saida_monitor
```

O gabarito deve conter:

```csv
incident_id,inicio,fim,tipo_alerta,line,station,jig_id,model,firmware_version,failed_step,error_code,severidade
```

Campos dimensionais podem ficar vazios quando não forem aplicáveis.

## Métricas

- Precisão: proporção de alertas gerados que correspondem a incidentes reais.
- Recall: proporção de incidentes reais que foram detectados.
- Latência média: tempo médio entre o início do incidente e o primeiro alerta correspondente.
- Taxa de falso alarme: proporção de alertas sem incidente correspondente.

## Arquivos Gerados

- `alertas.csv`: todos os alertas e candidatos enviados a revisão.
- `auditoria.csv`: janelas processadas e contadores de decisão.
- `revisao_humana.csv`: fila HITL.
- `avaliacao.csv`: métricas calculadas.
- `pareamentos_gabarito.csv`: correspondência entre alertas e incidentes.
- `relatorio_monitor.html`: resumo navegável da execução.
