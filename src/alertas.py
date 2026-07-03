from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha1
from typing import Any

import pandas as pd


COLUNAS_ALERTA = [
    "alert_id",
    "created_at",
    "window_start",
    "window_end",
    "tipo_alerta",
    "severidade",
    "line",
    "station",
    "jig_id",
    "model",
    "firmware_version",
    "failed_step",
    "error_code",
    "metrica",
    "valor_observado",
    "limiar",
    "evidencia",
    "acao_sugerida",
    "hitl_required",
    "status",
]


COLUNAS_REVISAO = [
    "alert_id",
    "timestamp_alerta",
    "severidade",
    "tipo_alerta",
    "evidencia",
    "acao_sugerida",
    "status_revisao",
    "decisao_humana",
    "responsavel",
    "timestamp_decisao",
    "observacao",
]


@dataclass
class Alerta:
    alert_id: str
    created_at: str
    window_start: str
    window_end: str
    tipo_alerta: str
    severidade: str
    line: str
    station: str
    jig_id: str
    model: str
    firmware_version: str
    failed_step: str
    error_code: str
    metrica: str
    valor_observado: float
    limiar: str
    evidencia: str
    acao_sugerida: str
    hitl_required: bool
    status: str

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


def gerar_alert_id(tipo: str, chave: str, window_end: pd.Timestamp) -> str:
    bruto = f"{tipo}|{chave}|{window_end.isoformat()}"
    return sha1(bruto.encode("utf-8")).hexdigest()[:12].upper()


def criar_alerta(
    candidato: dict[str, Any],
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    created_at: pd.Timestamp,
    status: str,
    hitl_required: bool,
    severidade: str | None = None,
) -> Alerta:
    tipo = str(candidato["tipo_alerta"])
    chave = str(candidato["chave"])
    severidade_final = severidade or str(candidato.get("severidade", "MEDIA"))
    return Alerta(
        alert_id=gerar_alert_id(tipo, chave, window_end),
        created_at=created_at.isoformat(),
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        tipo_alerta=tipo,
        severidade=severidade_final,
        line=str(candidato.get("line", "")),
        station=str(candidato.get("station", "")),
        jig_id=str(candidato.get("jig_id", "")),
        model=str(candidato.get("model", "")),
        firmware_version=str(candidato.get("firmware_version", "")),
        failed_step=str(candidato.get("failed_step", "")),
        error_code=str(candidato.get("error_code", "")),
        metrica=str(candidato.get("metrica", "")),
        valor_observado=float(candidato.get("valor_observado", 0)),
        limiar=str(candidato.get("limiar", "")),
        evidencia=str(candidato.get("evidencia", "")),
        acao_sugerida=str(candidato.get("acao_sugerida", "")),
        hitl_required=hitl_required,
        status=status,
    )


def montar_revisoes(alertas: list[Alerta]) -> pd.DataFrame:
    linhas = []
    for alerta in alertas:
        if not alerta.hitl_required:
            continue
        linhas.append(
            {
                "alert_id": alerta.alert_id,
                "timestamp_alerta": alerta.created_at,
                "severidade": alerta.severidade,
                "tipo_alerta": alerta.tipo_alerta,
                "evidencia": alerta.evidencia,
                "acao_sugerida": alerta.acao_sugerida,
                "status_revisao": "PENDENTE",
                "decisao_humana": "",
                "responsavel": "",
                "timestamp_decisao": "",
                "observacao": "",
            }
        )
    return pd.DataFrame(linhas, columns=COLUNAS_REVISAO)


def alertas_para_dataframe(alertas: list[Alerta]) -> pd.DataFrame:
    return pd.DataFrame([alerta.para_dict() for alerta in alertas], columns=COLUNAS_ALERTA)
