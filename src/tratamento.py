import pandas as pd


COLUNAS_NUMERICAS_FIXAS = [
    "attempt",
    "total_cycle_s",
    "cable_channels_found",
]


def tratar_gravacoes(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Ajusta os tipos principais da aba de gravações.
    dados = gravacoes.copy()
    dados["timestamp"] = pd.to_datetime(dados["timestamp"])
    dados["date"] = pd.to_datetime(dados["date"]).dt.date

    colunas_ciclo = [coluna for coluna in dados.columns if coluna.endswith("_cycle_s")]
    for coluna in COLUNAS_NUMERICAS_FIXAS + colunas_ciclo:
        if coluna in dados.columns:
            dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")

    if "attempt" in dados.columns:
        dados["attempt"] = dados["attempt"].astype("Int64")

    return dados


def tratar_paradas(paradas: pd.DataFrame) -> pd.DataFrame:
    # Ajusta os tipos principais da aba de paradas de linha.
    dados = paradas.copy()
    dados["stop_start"] = pd.to_datetime(dados["stop_start"])
    dados["stop_end"] = pd.to_datetime(dados["stop_end"])
    dados["duration_min"] = pd.to_numeric(dados["duration_min"], errors="coerce")
    return dados

