from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


ACOES_ERRO = {
    "ERR_AUTH": "Renovar ou validar API key antes de continuar o lote.",
    "ERR_DRM": "Revisar provisionamento de chaves DRM e bloquear liberação até validação.",
    "ERR_MD5": "Validar integridade dos artefatos de firmware e checksums.",
    "ERR_NO_SIGNAL": "Inspecionar cabo, tuner e modelo afetado.",
    "ERR_FLASH": "Inspecionar jig, memória e etapa de gravação.",
    "ERR_POWER": "Verificar alimentação, fonte e contatos do fixture.",
    "ERR_COMM": "Verificar comunicação entre jig, estação e dispositivo.",
    "ERR_USB": "Inspecionar porta/cabo USB e fixture.",
    "ERR_TIMEOUT": "Investigar lentidão de etapa e estabilidade da estação.",
    "ERR_GLITCH": "Acompanhar recorrência; tratar como ruído se isolado.",
}


@dataclass
class ConfigRegras:
    min_tentativas_jig: int = 30
    min_falhas_jig: int = 5
    taxa_falha_jig: float = 0.15
    min_seriais_firmware: int = 50
    queda_fpy_firmware: float = 0.08
    ppm_firmware: float = 180_000
    min_registros_cycle: int = 30
    fator_p95_cycle: float = 1.25
    min_falhas_erro: int = 4
    taxa_erro_critico: float = 0.05


def montar_baseline(gravacoes: pd.DataFrame) -> dict[str, Any]:
    return {
        "firmware": _baseline_firmware(gravacoes),
        "cycle_model": _baseline_cycle_model(gravacoes),
        "cycle_steps": _baseline_cycle_steps(gravacoes),
    }


def avaliar_regras(
    janela: pd.DataFrame,
    historico: pd.DataFrame,
    baseline: dict[str, Any],
    config: ConfigRegras,
) -> list[dict[str, Any]]:
    candidatos: list[dict[str, Any]] = []
    if janela.empty:
        return candidatos

    candidatos.extend(_regra_jig_etapa(janela, config))
    candidatos.extend(_regra_firmware(janela, baseline, config))
    candidatos.extend(_regra_cycle_time(janela, baseline, config))
    candidatos.extend(_regra_mac_duplicado(historico))
    candidatos.extend(_regra_erro_critico(janela, config))
    return candidatos


def _falhas(dados: pd.DataFrame) -> pd.DataFrame:
    return dados[(dados["result"] == "FAIL") & dados["error_code"].notna()].copy()


def _taxa_falha(dados: pd.DataFrame) -> float:
    if dados.empty:
        return 0
    return float((dados["result"] == "FAIL").sum() / len(dados))


def _fpy(dados: pd.DataFrame) -> float:
    if dados.empty:
        return 0
    total_seriais = dados["serial_number"].nunique()
    primeiras = dados[dados["attempt"] == 1]
    aprovados = primeiras[primeiras["result"] == "PASS"]["serial_number"].nunique()
    return float(aprovados / total_seriais) if total_seriais else 0


def _baseline_firmware(gravacoes: pd.DataFrame) -> pd.DataFrame:
    if gravacoes.empty:
        return pd.DataFrame(columns=["firmware_version", "model", "baseline_fpy"])
    linhas = []
    for (firmware, modelo), grupo in gravacoes.groupby(["firmware_version", "model"], dropna=False):
        linhas.append({"firmware_version": firmware, "model": modelo, "baseline_fpy": _fpy(grupo)})
    return pd.DataFrame(linhas)


def _baseline_cycle_model(gravacoes: pd.DataFrame) -> pd.DataFrame:
    if gravacoes.empty or "total_cycle_s" not in gravacoes:
        return pd.DataFrame(columns=["model", "baseline_p95_total"])
    return (
        gravacoes.groupby("model")["total_cycle_s"]
        .quantile(0.95)
        .reset_index(name="baseline_p95_total")
    )


def _baseline_cycle_steps(gravacoes: pd.DataFrame) -> dict[str, float]:
    colunas = [coluna for coluna in gravacoes.columns if coluna.endswith("_cycle_s") and coluna != "total_cycle_s"]
    return {coluna: float(gravacoes[coluna].quantile(0.95)) for coluna in colunas if gravacoes[coluna].notna().any()}


def _regra_jig_etapa(janela: pd.DataFrame, config: ConfigRegras) -> list[dict[str, Any]]:
    falhas = _falhas(janela)
    if falhas.empty:
        return []

    tentativas_jig = janela.groupby(["line", "station", "jig_id"], dropna=False).size().reset_index(name="tentativas")
    grupos = (
        falhas.groupby(["line", "station", "jig_id", "failed_step", "error_code"], dropna=False)
        .size()
        .reset_index(name="falhas")
        .merge(tentativas_jig, on=["line", "station", "jig_id"], how="left")
    )
    grupos["taxa"] = grupos["falhas"] / grupos["tentativas"]

    candidatos = []
    for _, linha in grupos.iterrows():
        if (
            linha["tentativas"] >= config.min_tentativas_jig
            and linha["falhas"] >= config.min_falhas_jig
            and linha["taxa"] >= config.taxa_falha_jig
        ):
            severidade = "ALTA" if linha["taxa"] >= 0.3 or linha["falhas"] >= 10 else "MEDIA"
            candidatos.append(
                {
                    "tipo_alerta": "FALHA_SISTEMATICA_JIG_ETAPA",
                    "chave": f"{linha['line']}|{linha['station']}|{linha['jig_id']}|{linha['failed_step']}|{linha['error_code']}",
                    "severidade": severidade,
                    "line": linha["line"],
                    "station": linha["station"],
                    "jig_id": linha["jig_id"],
                    "failed_step": linha["failed_step"],
                    "error_code": linha["error_code"],
                    "metrica": "taxa_falha_jig_etapa",
                    "valor_observado": linha["taxa"],
                    "limiar": f">= {config.taxa_falha_jig:.2%}, falhas >= {config.min_falhas_jig}",
                    "evidencia": f"{int(linha['falhas'])} falhas em {int(linha['tentativas'])} tentativas no jig.",
                    "acao_sugerida": "Parar ou isolar o jig e abrir manutenção se a recorrência persistir.",
                    "exige_recorrencia": True,
                }
            )
    return candidatos


def _regra_firmware(janela: pd.DataFrame, baseline: dict[str, Any], config: ConfigRegras) -> list[dict[str, Any]]:
    base = baseline["firmware"]
    candidatos = []

    for (firmware, modelo), grupo in janela.groupby(["firmware_version", "model"], dropna=False):
        seriais = grupo["serial_number"].nunique()
        if seriais < config.min_seriais_firmware:
            continue
        fpy_atual = _fpy(grupo)
        ppm = (1 - fpy_atual) * 1_000_000
        base_linha = base[(base["firmware_version"] == firmware) & (base["model"] == modelo)]
        baseline_fpy = float(base_linha["baseline_fpy"].iloc[0]) if not base_linha.empty else 0.9
        queda = baseline_fpy - fpy_atual
        if queda >= config.queda_fpy_firmware or ppm >= config.ppm_firmware:
            severidade = "ALTA" if queda >= 0.15 or ppm >= 300_000 else "MEDIA"
            candidatos.append(
                {
                    "tipo_alerta": "QUEDA_QUALIDADE_FIRMWARE",
                    "chave": f"{firmware}|{modelo}",
                    "severidade": severidade,
                    "model": modelo,
                    "firmware_version": firmware,
                    "metrica": "fpy_firmware",
                    "valor_observado": fpy_atual,
                    "limiar": f"queda >= {config.queda_fpy_firmware:.2%} ou PPM >= {config.ppm_firmware:.0f}",
                    "evidencia": f"FPY {fpy_atual:.2%}, baseline {baseline_fpy:.2%}, PPM {ppm:.0f}, seriais {seriais}.",
                    "acao_sugerida": "Bloquear ou revisar lote de firmware antes de continuar a produção.",
                    "exige_recorrencia": True,
                }
            )
    return candidatos


def _regra_cycle_time(janela: pd.DataFrame, baseline: dict[str, Any], config: ConfigRegras) -> list[dict[str, Any]]:
    candidatos = []
    base_model = baseline["cycle_model"]

    for modelo, grupo in janela.groupby("model", dropna=False):
        if len(grupo) < config.min_registros_cycle or "total_cycle_s" not in grupo:
            continue
        p95 = float(grupo["total_cycle_s"].quantile(0.95))
        base_linha = base_model[base_model["model"] == modelo]
        baseline_p95 = float(base_linha["baseline_p95_total"].iloc[0]) if not base_linha.empty else p95
        limite = baseline_p95 * config.fator_p95_cycle
        if p95 > limite:
            candidatos.append(
                {
                    "tipo_alerta": "DRIFT_CYCLE_TIME",
                    "chave": f"total|{modelo}",
                    "severidade": "MEDIA" if p95 < limite * 1.25 else "ALTA",
                    "model": modelo,
                    "metrica": "p95_total_cycle_s",
                    "valor_observado": p95,
                    "limiar": f"> {limite:.1f}s",
                    "evidencia": f"P95 total {p95:.1f}s contra baseline {baseline_p95:.1f}s.",
                    "acao_sugerida": "Investigar gargalo de ciclo e correlacionar com falhas ou paradas.",
                    "exige_recorrencia": True,
                }
            )

    for coluna, baseline_p95 in baseline["cycle_steps"].items():
        valores = janela[coluna].dropna() if coluna in janela else pd.Series(dtype=float)
        if len(valores) < config.min_registros_cycle:
            continue
        p95 = float(valores.quantile(0.95))
        limite = baseline_p95 * config.fator_p95_cycle
        if p95 > limite:
            candidatos.append(
                {
                    "tipo_alerta": "DRIFT_CYCLE_TIME_ETAPA",
                    "chave": coluna,
                    "severidade": "MEDIA",
                    "failed_step": coluna.removesuffix("_cycle_s"),
                    "metrica": "p95_step_cycle_s",
                    "valor_observado": p95,
                    "limiar": f"> {limite:.1f}s",
                    "evidencia": f"P95 de {coluna} em {p95:.1f}s contra baseline {baseline_p95:.1f}s.",
                    "acao_sugerida": "Inspecionar etapa com aumento de tempo de ciclo.",
                    "exige_recorrencia": True,
                }
            )
    return candidatos


def _regra_mac_duplicado(historico: pd.DataFrame) -> list[dict[str, Any]]:
    if historico.empty or "mac_address" not in historico:
        return []
    resumo = (
        historico.dropna(subset=["mac_address"])
        .groupby("mac_address")
        .agg(
            seriais=("serial_number", "nunique"),
            tentativas=("serial_number", "count"),
            lista_seriais=("serial_number", lambda valores: ", ".join(sorted(set(valores.astype(str)))[:5])),
        )
        .reset_index()
    )
    duplicados = resumo[resumo["seriais"] > 1]
    candidatos = []
    for _, linha in duplicados.iterrows():
        candidatos.append(
            {
                "tipo_alerta": "MAC_DUPLICADO",
                "chave": linha["mac_address"],
                "severidade": "ALTA",
                "metrica": "seriais_por_mac",
                "valor_observado": linha["seriais"],
                "limiar": "> 1 serial por MAC",
                "evidencia": f"MAC {linha['mac_address']} aparece em {int(linha['seriais'])} seriais: {linha['lista_seriais']}.",
                "acao_sugerida": "Bloquear liberação dos seriais e revisar provisionamento de MAC.",
                "exige_recorrencia": False,
            }
        )
    return candidatos


def _regra_erro_critico(janela: pd.DataFrame, config: ConfigRegras) -> list[dict[str, Any]]:
    falhas = _falhas(janela)
    if falhas.empty:
        return []
    total = len(janela)
    candidatos = []
    resumo = falhas.groupby("error_code").size().reset_index(name="falhas")
    for _, linha in resumo.iterrows():
        taxa = float(linha["falhas"] / total) if total else 0
        erro = str(linha["error_code"])
        if linha["falhas"] >= config.min_falhas_erro and taxa >= config.taxa_erro_critico:
            candidatos.append(
                {
                    "tipo_alerta": "ERRO_CRITICO_RECORRENTE",
                    "chave": erro,
                    "severidade": "ALTA" if erro in {"ERR_AUTH", "ERR_DRM", "ERR_MD5"} else "MEDIA",
                    "error_code": erro,
                    "metrica": "taxa_erro_critico",
                    "valor_observado": taxa,
                    "limiar": f">= {config.taxa_erro_critico:.2%}, falhas >= {config.min_falhas_erro}",
                    "evidencia": f"{int(linha['falhas'])} ocorrencias de {erro} em {total} tentativas.",
                    "acao_sugerida": ACOES_ERRO.get(erro, "Investigar recorrência do erro e registrar ação corretiva."),
                    "exige_recorrencia": erro == "ERR_GLITCH",
                }
            )
    return candidatos
