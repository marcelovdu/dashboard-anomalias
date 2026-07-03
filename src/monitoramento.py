from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pandas as pd

from src.carregar_dados import ABA_GRAVACOES, ABA_PARADAS
from src.tratamento import tratar_gravacoes, tratar_paradas


def carregar_logs(caminho: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    alvo = Path(caminho)
    arquivos = _listar_arquivos(alvo)
    gravacoes = []
    paradas = []

    for arquivo in arquivos:
        if arquivo.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
            excel = pd.ExcelFile(arquivo)
            if ABA_GRAVACOES in excel.sheet_names:
                gravacoes.append(pd.read_excel(excel, sheet_name=ABA_GRAVACOES))
            if ABA_PARADAS in excel.sheet_names:
                paradas.append(pd.read_excel(excel, sheet_name=ABA_PARADAS))
        elif arquivo.suffix.lower() == ".csv":
            gravacoes.append(pd.read_csv(arquivo))

    if not gravacoes:
        raise FileNotFoundError(f"Nenhum log de gravacoes encontrado em {alvo}.")

    dados_gravacoes = tratar_gravacoes(pd.concat(gravacoes, ignore_index=True))
    dados_gravacoes = dados_gravacoes.sort_values("timestamp").reset_index(drop=True)

    if paradas:
        dados_paradas = tratar_paradas(pd.concat(paradas, ignore_index=True))
        dados_paradas = dados_paradas.sort_values("stop_start").reset_index(drop=True)
    else:
        dados_paradas = pd.DataFrame(columns=["line", "stop_start", "stop_end", "duration_min", "reason", "category"])

    return dados_gravacoes, dados_paradas


def _listar_arquivos(alvo: Path) -> list[Path]:
    if alvo.is_file():
        return [alvo]
    if not alvo.exists():
        raise FileNotFoundError(f"Caminho não encontrado: {alvo}")
    return sorted(
        [
            arquivo
            for arquivo in alvo.iterdir()
            if arquivo.is_file() and arquivo.suffix.lower() in {".xlsx", ".xlsm", ".xls", ".csv"}
        ]
    )


def recorte_baseline(gravacoes: pd.DataFrame, horas: int) -> pd.DataFrame:
    if gravacoes.empty:
        return gravacoes.copy()
    inicio = gravacoes["timestamp"].min()
    fim = inicio + pd.Timedelta(hours=horas)
    base = gravacoes[gravacoes["timestamp"] <= fim].copy()
    if base.empty:
        return gravacoes.head(max(1, int(len(gravacoes) * 0.2))).copy()
    return base


def iterar_janelas(
    gravacoes: pd.DataFrame,
    minutos_janela: int,
    minutos_passo: int,
    inicio_monitoramento: pd.Timestamp | None = None,
) -> Iterator[tuple[pd.Timestamp, pd.Timestamp, pd.DataFrame]]:
    if gravacoes.empty:
        return

    primeiro = gravacoes["timestamp"].min()
    ultimo = gravacoes["timestamp"].max()
    janela = pd.Timedelta(minutes=minutos_janela)
    passo = pd.Timedelta(minutes=minutos_passo)
    fim = inicio_monitoramento or primeiro + janela

    while fim <= ultimo + pd.Timedelta(seconds=1):
        inicio = fim - janela
        dados = gravacoes[(gravacoes["timestamp"] > inicio) & (gravacoes["timestamp"] <= fim)].copy()
        yield inicio, fim, dados
        fim += passo


def filtrar_paradas_janela(paradas: pd.DataFrame, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    if paradas.empty:
        return paradas.copy()
    return paradas[(paradas["stop_start"] <= fim) & (paradas["stop_end"] >= inicio)].copy()
