# PDD - Monitor de Anomalias

## Objetivo

Construir um monitor automático para logs de gravação de setupbox. O monitor processa os dados em janelas móveis, detecta anomalias, classifica severidade, recomenda ação, registra auditoria e separa casos que exigem revisão humana.

## Escopo

Inclui:

- ingestão de arquivo Excel único, pasta de arquivos Excel ou arquivos CSV;
- uso da aba `recordings` como log principal;
- uso da aba `line_stops` para contexto de paradas;
- processamento em janelas móveis;
- regras baseline reproduzíveis;
- alertas CSV, auditoria CSV, fila HITL CSV e relatório HTML.

Não inclui:

- banco de dados;
- Docker;
- deploy;
- envio real por Telegram/e-mail;
- decisão automática irreversível em equipamento físico.

## Entradas

- `recording_test_setupbox.xlsx`, ou pasta com logs equivalentes.
- Aba `recordings`: tentativas de gravação.
- Aba `line_stops`: paradas de linha.
- Gabarito opcional em CSV para avaliação.

Formato sugerido do gabarito:

```csv
incident_id,inicio,fim,tipo_alerta,line,station,jig_id,model,firmware_version,failed_step,error_code,severidade
```

## Saídas

- `saida_monitor/alertas.csv`
- `saida_monitor/auditoria.csv`
- `saida_monitor/revisao_humana.csv`
- `saida_monitor/avaliacao.csv`
- `saida_monitor/pareamentos_gabarito.csv`
- `saida_monitor/relatorio_monitor.html`

## Baseline

O baseline padrão é calculado sobre as primeiras 12 horas do log, configurável por `--baseline-hours`.

Métricas de baseline:

- FPY por `firmware_version` e `model`;
- p95 de `total_cycle_s` por modelo;
- p95 das colunas `*_cycle_s` por etapa;
- histórico acumulado para MAC duplicado.

## Janela Móvel

Padrão:

- tamanho da janela: 60 minutos;
- passo entre janelas: 15 minutos;
- confirmação sistemática: 2 janelas consecutivas.

Configuração via CLI:

```bash
python monitor.py --window-minutes 60 --step-minutes 15 --min-consecutive 2
```

## Regras de Detecção

### Falha sistemática por jig e etapa

Agrupamento:

- `line`
- `station`
- `jig_id`
- `failed_step`
- `error_code`

Limiar inicial:

- pelo menos 30 tentativas no jig na janela;
- pelo menos 5 falhas na combinação;
- taxa de falha igual ou superior a 15%;
- recorrência em 2 janelas para confirmar como sistemática.

Ação sugerida:

- isolar/parar jig;
- abrir manutenção;
- acompanhar próxima janela se ainda estiver ambíguo.

### Queda de qualidade por firmware

Agrupamento:

- `firmware_version`
- `model`

Limiar inicial:

- pelo menos 50 seriais na janela;
- queda de FPY de 8 pontos percentuais contra baseline;
- ou PPM maior ou igual a 180.000.

Ação sugerida:

- bloquear ou revisar lote de firmware;
- acionar qualidade/engenharia.

### Drift de cycle time

Métricas:

- p95 de `total_cycle_s`;
- p95 das etapas `*_cycle_s`.

Limiar inicial:

- pelo menos 30 registros na janela;
- p95 da janela maior que 1,25 vezes o p95 do baseline.

Ação sugerida:

- investigar gargalo;
- correlacionar com paradas e falhas;
- abrir manutenção se combinado com falha recorrente.

### MAC duplicado

Regra:

- o mesmo `mac_address` aparece em mais de um `serial_number`.

Ação sugerida:

- bloquear liberação dos seriais;
- revisar provisionamento;
- enviar obrigatoriamente para HITL.

### Erro crítico recorrente

Limiar inicial:

- pelo menos 4 ocorrências do erro na janela;
- taxa do erro igual ou superior a 5% das tentativas.

Runbook:

- `ERR_AUTH`: renovar ou validar API key;
- `ERR_DRM`: revisar provisionamento de chaves DRM;
- `ERR_MD5`: validar integridade de artefatos de firmware;
- `ERR_NO_SIGNAL`: inspecionar cabo, tuner e modelo afetado;
- `ERR_FLASH`: revisar jig, memória ou etapa de gravação;
- `ERR_GLITCH`: tratar como ruído se isolado e alertar apenas se recorrente.

## Severidade

- `BAIXA`: candidato ambíguo, primeira ocorrência ou baixo volume. Vai para revisão se a regra ainda não foi confirmada.
- `MEDIA`: anomalia recorrente com impacto operacional controlado.
- `ALTA`: risco de scrap, bloqueio, MAC duplicado, erro crítico ou queda forte de qualidade.
- `CRITICA`: reservada para decisão humana quando a equipe definir bloqueio amplo de linha/lote.

## HITL

Casos enviados para revisão humana:

- alertas de severidade alta ou crítica;
- candidatos ambíguos ainda não confirmados;
- MAC duplicado;
- recomendações de bloqueio de lote, firmware ou liberação de serial.

O arquivo `saida_monitor/revisao_humana.csv` contém campos para decisão humana, responsável, data e observação.

## Avaliação

Quando um gabarito for fornecido, o monitor calcula:

- precisão;
- recall;
- latência média de detecção;
- taxa de falso alarme.

Sem gabarito, o arquivo de avaliação registra que as métricas ficam pendentes.
