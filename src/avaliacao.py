from __future__ import annotations

from pathlib import Path

import pandas as pd


COLUNAS_AVALIACAO = ["metrica", "valor"]


def avaliar_alertas(alertas: pd.DataFrame, caminho_gabarito: str | Path | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not caminho_gabarito:
        return _sem_gabarito(), pd.DataFrame()

    caminho = Path(caminho_gabarito)
    if not caminho.exists() or alertas.empty:
        return _sem_gabarito(), pd.DataFrame()

    gabarito = pd.read_csv(caminho)
    if gabarito.empty:
        return _sem_gabarito(), pd.DataFrame()

    alertas = alertas.copy()
    gabarito = gabarito.copy()
    alertas["created_at"] = pd.to_datetime(alertas["created_at"])
    gabarito["inicio"] = pd.to_datetime(gabarito["inicio"])
    gabarito["fim"] = pd.to_datetime(gabarito["fim"])

    pareamentos = []
    incidentes_detectados = set()
    alertas_verdadeiros = set()

    for idx_alerta, alerta in alertas.iterrows():
        candidatos = gabarito[gabarito.apply(lambda inc: _combina(alerta, inc), axis=1)]
        if candidatos.empty:
            continue
        incidente = candidatos.sort_values("inicio").iloc[0]
        incidentes_detectados.add(incidente["incident_id"])
        alertas_verdadeiros.add(idx_alerta)
        latencia_min = (alerta["created_at"] - incidente["inicio"]).total_seconds() / 60
        pareamentos.append(
            {
                "alert_id": alerta["alert_id"],
                "incident_id": incidente["incident_id"],
                "latencia_min": max(latencia_min, 0),
            }
        )

    total_alertas = len(alertas)
    total_incidentes = len(gabarito)
    verdadeiros = len(alertas_verdadeiros)
    detectados = len(incidentes_detectados)
    falsos = total_alertas - verdadeiros
    latencias = [p["latencia_min"] for p in pareamentos]

    metricas = pd.DataFrame(
        [
            {"metrica": "precisão", "valor": verdadeiros / total_alertas if total_alertas else 0},
            {"metrica": "recall", "valor": detectados / total_incidentes if total_incidentes else 0},
            {"metrica": "latência_média_min", "valor": sum(latencias) / len(latencias) if latencias else 0},
            {"metrica": "taxa_falso_alarme", "valor": falsos / total_alertas if total_alertas else 0},
            {"metrica": "alertas", "valor": total_alertas},
            {"metrica": "incidentes", "valor": total_incidentes},
        ],
        columns=COLUNAS_AVALIACAO,
    )
    return metricas, pd.DataFrame(pareamentos)


def _sem_gabarito() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"metrica": "precisão", "valor": ""},
            {"metrica": "recall", "valor": ""},
            {"metrica": "latência_média_min", "valor": ""},
            {"metrica": "taxa_falso_alarme", "valor": ""},
            {"metrica": "observação", "valor": "Gabarito não informado; métricas ficam pendentes."},
        ],
        columns=COLUNAS_AVALIACAO,
    )


def _combina(alerta: pd.Series, incidente: pd.Series) -> bool:
    tolerancia = pd.Timedelta(hours=1)
    if alerta["created_at"] < incidente["inicio"] or alerta["created_at"] > incidente["fim"] + tolerancia:
        return False

    for coluna in ["tipo_alerta", "line", "station", "jig_id", "model", "firmware_version", "failed_step", "error_code"]:
        if coluna not in incidente or pd.isna(incidente[coluna]) or str(incidente[coluna]) == "":
            continue
        if coluna not in alerta or str(alerta[coluna]) != str(incidente[coluna]):
            return False
    return True
