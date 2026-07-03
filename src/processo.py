BPMN_IMAGEM = "assets/bpmn_setupbox.png"


PDD_SECOES = [
    {
        "titulo": "Objetivo",
        "itens": [
            "Analisar o processo de gravação de setupboxes e identificar anomalias de qualidade, tempo, equipamento e disponibilidade.",
            "Dar suporte à decisão antes de qualquer automação, mostrando onde o processo falha, quando falha e por quanto tempo.",
        ],
    },
    {
        "titulo": "Escopo",
        "itens": [
            "Inclui tentativas de gravação registradas na aba recordings.",
            "Inclui eventos de parada registrados na aba line_stops.",
            "Inclui análise por linha, estação, jig, operador, modelo, firmware, etapa, erro, turno e disposition.",
            "Não inclui integração com banco de dados, serviços externos ou automação em produção.",
        ],
    },
    {
        "titulo": "Entradas",
        "itens": [
            "Arquivo recording_test_setupbox.xlsx.",
            "Aba recordings com histórico das tentativas de gravação.",
            "Aba line_stops com paradas de linha.",
            "Aba data_dictionary com descrição das colunas.",
        ],
    },
    {
        "titulo": "Saídas",
        "itens": [
            "Dashboard de análise e auditoria.",
            "KPIs de FPY, PPM, throughput, downtime, yield final, rework e scrap.",
            "Pareto de defeitos, visão jig x etapa, falhas no tempo e análise de cycle time.",
            "Relatório exportável com achados reproduzíveis por filtros.",
        ],
    },
    {
        "titulo": "Regras de negócio",
        "itens": [
            "Uma unidade aprovada na primeira tentativa conta para FPY.",
            "Se a primeira tentativa falha, o mesmo serial deve voltar como attempt 2.",
            "Falha na primeira tentativa recebe disposition REWORK.",
            "Falha novamente após rework recebe disposition SCRAP.",
            "Etapas não aplicáveis ao modelo podem ficar em branco, como Bluetooth ou cable_scan.",
            "MAC address deve ser único entre seriais diferentes.",
        ],
    },
    {
        "titulo": "Exceções e anomalias monitoradas",
        "itens": [
            "Falha sistemática por jig ou estação.",
            "Falha de download/autenticação remota por API key.",
            "Firmware ou modelo com queda de rendimento.",
            "Perda de sinal em modelos com cabo.",
            "Cycle time acima do p95.",
            "MAC duplicado em seriais diferentes.",
            "Aumento de scrap por erro específico.",
        ],
    },
    {
        "titulo": "Pontos de monitoramento e automação futura",
        "itens": [
            "Alertar quando um jig concentrar falhas acima do comportamento normal.",
            "Alertar quando a taxa de falha por hora subir junto de parada de linha.",
            "Bloquear ou revisar lote de firmware com FPY crítico.",
            "Notificar manutenção quando cycle time ou falhas por etapa passarem do limite.",
            "Auditar MAC duplicado antes da liberação do produto.",
        ],
    },
]

