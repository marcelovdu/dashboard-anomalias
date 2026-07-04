import pandas as pd


def filtrar_falhas(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Mantém somente tentativas com falha e com código de erro preenchido.
    return gravacoes[(gravacoes["result"] == "FAIL") & (gravacoes["error_code"].notna())].copy()


def calcular_kpis_basicos(gravacoes: pd.DataFrame, paradas: pd.DataFrame) -> dict[str, float | int]:
    # Calcula os indicadores principais da visão geral.
    total_tentativas = len(gravacoes)
    total_seriais = gravacoes["serial_number"].nunique()

    primeiras_tentativas = gravacoes[gravacoes["attempt"] == 1]
    aprovados_primeira = primeiras_tentativas[primeiras_tentativas["result"] == "PASS"]["serial_number"].nunique()

    seriais_aprovados = gravacoes[gravacoes["result"] == "PASS"]["serial_number"].nunique()
    seriais_retrabalho = gravacoes[gravacoes["disposition"] == "REWORK"]["serial_number"].nunique()
    seriais_sucata = gravacoes[gravacoes["disposition"] == "SCRAP"]["serial_number"].nunique()

    fpy = aprovados_primeira / total_seriais if total_seriais else 0
    rendimento_final = seriais_aprovados / total_seriais if total_seriais else 0
    taxa_retrabalho = seriais_retrabalho / total_seriais if total_seriais else 0
    taxa_sucata = seriais_sucata / total_seriais if total_seriais else 0
    ppm = (1 - fpy) * 1_000_000

    parada_min = paradas["duration_min"].sum() if "duration_min" in paradas else 0
    horas_planejadas = calcular_horas_planejadas(gravacoes)
    uph = total_seriais / horas_planejadas if horas_planejadas else 0
    disponibilidade = (horas_planejadas - parada_min / 60) / horas_planejadas if horas_planejadas else 0

    return {
        "total_tentativas": total_tentativas,
        "total_seriais": total_seriais,
        "fpy": fpy,
        "ppm": ppm,
        "rendimento_final": rendimento_final,
        "taxa_retrabalho": taxa_retrabalho,
        "taxa_sucata": taxa_sucata,
        "parada_min": parada_min,
        "horas_planejadas": horas_planejadas,
        "uph": uph,
        "disponibilidade": max(disponibilidade, 0),
    }


def calcular_horas_planejadas(gravacoes: pd.DataFrame) -> float:
    # Soma a janela observada de produção por linha.
    if gravacoes.empty or "timestamp" not in gravacoes:
        return 0

    horas_por_linha = (
        gravacoes.groupby("line")["timestamp"]
        .agg(["min", "max"])
        .assign(horas=lambda dados: (dados["max"] - dados["min"]).dt.total_seconds() / 3600)
    )
    return float(horas_por_linha["horas"].sum())


def montar_pareto_defeitos(gravacoes: pd.DataFrame, coluna: str = "error_code") -> pd.DataFrame:
    # Monta a base do Pareto com quantidade, percentual e percentual acumulado.
    falhas = filtrar_falhas(gravacoes)
    if falhas.empty or coluna not in falhas:
        return pd.DataFrame(columns=[coluna, "quantidade", "percentual", "percentual_acumulado"])

    pareto = falhas[coluna].value_counts().reset_index()
    pareto.columns = [coluna, "quantidade"]
    total = pareto["quantidade"].sum()
    pareto["percentual"] = pareto["quantidade"] / total
    pareto["percentual_acumulado"] = pareto["percentual"].cumsum()
    return pareto


def montar_matriz_jig_etapa(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Agrupa falhas por jig e etapa para evidenciar equipamentos crônicos.
    falhas = filtrar_falhas(gravacoes)
    if falhas.empty:
        return pd.DataFrame()

    matriz = pd.pivot_table(
        falhas,
        index="jig_id",
        columns="failed_step",
        values="serial_number",
        aggfunc="count",
        fill_value=0,
    )
    matriz["total"] = matriz.sum(axis=1)
    matriz = matriz.sort_values("total", ascending=False).drop(columns="total")
    return matriz


def montar_ranking_jig_etapa(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Lista as combinações jig-etapa com mais falhas.
    falhas = filtrar_falhas(gravacoes)
    if falhas.empty:
        return pd.DataFrame(columns=["jig_id", "failed_step", "error_code", "quantidade"])

    return (
        falhas.groupby(["jig_id", "failed_step", "error_code"])
        .size()
        .reset_index(name="quantidade")
        .sort_values("quantidade", ascending=False)
    )


def montar_falhas_por_hora(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Agrupa tentativas, falhas e taxa de falha por hora.
    if gravacoes.empty:
        return pd.DataFrame(columns=["hora", "tentativas", "falhas", "taxa_falha"])

    dados = gravacoes.copy()
    dados["hora"] = dados["timestamp"].dt.floor("h")
    resumo = (
        dados.groupby("hora")
        .agg(
            tentativas=("serial_number", "count"),
            falhas=("result", lambda coluna: (coluna == "FAIL").sum()),
        )
        .reset_index()
    )
    resumo["taxa_falha"] = resumo["falhas"] / resumo["tentativas"]
    return resumo


def montar_falhas_por_hora_erro(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Agrupa falhas por hora e código de erro.
    falhas = filtrar_falhas(gravacoes)
    if falhas.empty:
        return pd.DataFrame(columns=["hora", "error_code", "falhas"])

    dados = falhas.copy()
    dados["hora"] = dados["timestamp"].dt.floor("h")
    return dados.groupby(["hora", "error_code"]).size().reset_index(name="falhas")


def listar_colunas_ciclo(gravacoes: pd.DataFrame) -> list[str]:
    # Identifica as colunas de tempo de ciclo das etapas.
    return [coluna for coluna in gravacoes.columns if coluna.endswith("_cycle_s") and coluna != "total_cycle_s"]


def montar_resumo_cycle_time(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Calcula estatísticas de tempo por etapa.
    colunas_ciclo = listar_colunas_ciclo(gravacoes)
    linhas = []

    for coluna in colunas_ciclo:
        valores = gravacoes[coluna].dropna()
        if valores.empty:
            continue

        etapa = coluna.removesuffix("_cycle_s")
        linhas.append(
            {
                "etapa": etapa,
                "registros": int(valores.count()),
                "media_s": valores.mean(),
                "mediana_s": valores.median(),
                "p95_s": valores.quantile(0.95),
                "max_s": valores.max(),
            }
        )

    if not linhas:
        return pd.DataFrame(columns=["etapa", "registros", "media_s", "mediana_s", "p95_s", "max_s"])

    return pd.DataFrame(linhas).sort_values("media_s", ascending=False)


def montar_outliers_cycle_time(gravacoes: pd.DataFrame, limite_p95: bool = True) -> pd.DataFrame:
    # Lista registros acima do p95 da etapa ou acima do p95 do total.
    if gravacoes.empty:
        return pd.DataFrame()

    dados = gravacoes.copy()
    if limite_p95:
        limite_total = dados["total_cycle_s"].quantile(0.95)
    else:
        limite_total = dados["total_cycle_s"].median() * 1.5

    colunas = [
        "timestamp",
        "line",
        "station",
        "jig_id",
        "model",
        "firmware_version",
        "serial_number",
        "attempt",
        "result",
        "failed_step",
        "error_code",
        "total_cycle_s",
    ]
    return dados[dados["total_cycle_s"] > limite_total][colunas].sort_values("total_cycle_s", ascending=False)


def calcular_indicadores_grupo(grupo: pd.DataFrame) -> pd.Series:
    # Calcula yield, rework e scrap para um grupo de registros.
    total_seriais = grupo["serial_number"].nunique()
    primeiras = grupo[grupo["attempt"] == 1]
    aprovados_primeira = primeiras[primeiras["result"] == "PASS"]["serial_number"].nunique()
    aprovados_final = grupo[grupo["result"] == "PASS"]["serial_number"].nunique()
    retrabalho = grupo[grupo["disposition"] == "REWORK"]["serial_number"].nunique()
    sucata = grupo[grupo["disposition"] == "SCRAP"]["serial_number"].nunique()

    return pd.Series(
        {
            "seriais": total_seriais,
            "tentativas": len(grupo),
            "fpy": aprovados_primeira / total_seriais if total_seriais else 0,
            "yield_final": aprovados_final / total_seriais if total_seriais else 0,
            "taxa_rework": retrabalho / total_seriais if total_seriais else 0,
            "taxa_scrap": sucata / total_seriais if total_seriais else 0,
        }
    )


def montar_yield_por_dimensao(gravacoes: pd.DataFrame, dimensao: str) -> pd.DataFrame:
    # Monta uma tabela de rendimento por dimensão produtiva.
    if gravacoes.empty or dimensao not in gravacoes:
        return pd.DataFrame()

    resumo = gravacoes.groupby(dimensao).apply(calcular_indicadores_grupo, include_groups=False).reset_index()
    return resumo.sort_values(["fpy", "seriais"], ascending=[True, False])


def montar_rework_scrap_por_erro(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Mostra quais erros aparecem mais em retrabalho e sucata.
    falhas = filtrar_falhas(gravacoes)
    if falhas.empty:
        return pd.DataFrame(columns=["error_code", "rework", "scrap", "total"])

    tabela = pd.pivot_table(
        falhas,
        index="error_code",
        columns="disposition",
        values="serial_number",
        aggfunc="count",
        fill_value=0,
    )
    for coluna in ["REWORK", "SCRAP"]:
        if coluna not in tabela:
            tabela[coluna] = 0

    tabela = tabela.rename(columns={"REWORK": "rework", "SCRAP": "scrap"})
    tabela["total"] = tabela["rework"] + tabela["scrap"]
    return tabela.reset_index().sort_values("total", ascending=False)


def montar_macs_duplicados(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Identifica MACs associados a mais de um serial diferente.
    if gravacoes.empty:
        return pd.DataFrame(columns=["mac_address", "seriais_distintos", "tentativas", "seriais"])

    resumo = (
        gravacoes.groupby("mac_address")
        .agg(
            seriais_distintos=("serial_number", "nunique"),
            tentativas=("serial_number", "count"),
            seriais=("serial_number", lambda valores: ", ".join(sorted(set(valores.astype(str))))),
        )
        .reset_index()
    )
    return resumo[resumo["seriais_distintos"] > 1].sort_values(
        ["seriais_distintos", "tentativas"],
        ascending=False,
    )


def montar_tentativas_por_serial(gravacoes: pd.DataFrame) -> pd.DataFrame:
    # Resume seriais que aparecem mais de uma vez, o que representa rework no processo.
    if gravacoes.empty:
        return pd.DataFrame(columns=["serial_number", "tentativas", "resultado_final", "erros"])

    resumo = (
        gravacoes.groupby("serial_number")
        .agg(
            tentativas=("attempt", "max"),
            primeira_data=("timestamp", "min"),
            ultima_data=("timestamp", "max"),
            resultado_final=("disposition", "last"),
            erros=("error_code", lambda valores: ", ".join(sorted(set(valores.dropna().astype(str))))),
        )
        .reset_index()
    )
    return resumo[resumo["tentativas"] > 1].sort_values(["tentativas", "ultima_data"], ascending=False)


def montar_resumo_auditoria(gravacoes: pd.DataFrame) -> dict[str, int]:
    # Consolida contagens rápidas para a aba de auditoria.
    macs_duplicados = montar_macs_duplicados(gravacoes)
    tentativas_rework = montar_tentativas_por_serial(gravacoes)
    return {
        "macs_duplicados": len(macs_duplicados),
        "seriais_com_rework": len(tentativas_rework),
        "scrap": int((gravacoes["disposition"] == "SCRAP").sum()) if not gravacoes.empty else 0,
        "falhas": int((gravacoes["result"] == "FAIL").sum()) if not gravacoes.empty else 0,
    }

