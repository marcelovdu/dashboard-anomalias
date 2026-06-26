from pathlib import Path

import pandas as pd


ABA_GRAVACOES = "recordings"
ABA_PARADAS = "line_stops"
ABA_DICIONARIO = "data_dictionary"


def carregar_planilha(caminho: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Carrega as três abas esperadas na planilha da atividade.
    caminho_planilha = Path(caminho)
    gravacoes = pd.read_excel(caminho_planilha, sheet_name=ABA_GRAVACOES)
    paradas = pd.read_excel(caminho_planilha, sheet_name=ABA_PARADAS)
    dicionario = pd.read_excel(caminho_planilha, sheet_name=ABA_DICIONARIO)
    return gravacoes, paradas, dicionario
