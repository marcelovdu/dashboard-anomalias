from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.carregar_dados import carregar_planilha
from src.metricas import (
    calcular_kpis_basicos,
    montar_macs_duplicados,
    montar_rework_scrap_por_erro,
    montar_outliers_cycle_time,
    montar_falhas_por_hora,
    montar_falhas_por_hora_erro,
    montar_matriz_jig_etapa,
    montar_pareto_defeitos,
    montar_ranking_jig_etapa,
    montar_resumo_auditoria,
    montar_resumo_cycle_time,
    montar_tentativas_por_serial,
    montar_yield_por_dimensao,
)
from src.processo import BPMN_IMAGEM, PDD_SECOES
from src.relatorio import gerar_relatorio_html, gerar_relatorio_pdf, montar_achados
from src.tratamento import tratar_gravacoes, tratar_paradas


st.set_page_config(
    page_title="Dashboard de Anomalias - Setupbox",
    page_icon="",
    layout="wide",
)


ARQUIVO_DADOS = "recording_test_setupbox.xlsx"


@st.cache_data(show_spinner="Carregando planilha...")
def carregar_dados(caminho: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    gravacoes, paradas, dicionario = carregar_planilha(caminho)
    return tratar_gravacoes(gravacoes), tratar_paradas(paradas), dicionario


def formatar_percentual(valor: float) -> str:
    return f"{valor * 100:.2f}%"


def formatar_numero(valor: float | int) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def opcoes_coluna(dados: pd.DataFrame, coluna: str) -> list[str]:
    valores = dados[coluna].dropna().astype(str).unique().tolist()
    return sorted(valores)


def seletor_multivalor(rotulo: str, dados: pd.DataFrame, coluna: str) -> list[str]:
    opcoes = opcoes_coluna(dados, coluna)
    return st.sidebar.multiselect(rotulo, opcoes, default=opcoes)


def filtrar_gravacoes(gravacoes: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    menor_data = gravacoes["timestamp"].min().date()
    maior_data = gravacoes["timestamp"].max().date()

    periodo = st.sidebar.date_input("Período", value=(menor_data, maior_data))
    if len(periodo) != 2:
        periodo = (menor_data, maior_data)

    filtros = {
        "periodo": periodo,
        "linhas": seletor_multivalor("Linha", gravacoes, "line"),
        "estacoes": seletor_multivalor("Estação", gravacoes, "station"),
        "jigs": seletor_multivalor("Jig", gravacoes, "jig_id"),
        "modelos": seletor_multivalor("Modelo", gravacoes, "model"),
        "firmwares": seletor_multivalor("Firmware", gravacoes, "firmware_version"),
        "turnos": seletor_multivalor("Turno", gravacoes, "shift"),
        "disposicoes": seletor_multivalor("Disposition", gravacoes, "disposition"),
    }

    erros = ["Todos"] + opcoes_coluna(gravacoes[gravacoes["error_code"].notna()], "error_code")
    erro_escolhido = st.sidebar.selectbox("Erro", erros)
    filtros["erro"] = erro_escolhido

    inicio, fim = periodo
    dados = gravacoes[
        (gravacoes["timestamp"].dt.date >= inicio)
        & (gravacoes["timestamp"].dt.date <= fim)
        & (gravacoes["line"].astype(str).isin(filtros["linhas"]))
        & (gravacoes["station"].astype(str).isin(filtros["estacoes"]))
        & (gravacoes["jig_id"].astype(str).isin(filtros["jigs"]))
        & (gravacoes["model"].astype(str).isin(filtros["modelos"]))
        & (gravacoes["firmware_version"].astype(str).isin(filtros["firmwares"]))
        & (gravacoes["shift"].astype(str).isin(filtros["turnos"]))
        & (gravacoes["disposition"].astype(str).isin(filtros["disposicoes"]))
    ]

    if erro_escolhido != "Todos":
        dados = dados[dados["error_code"] == erro_escolhido]

    return dados, filtros


def filtrar_paradas(paradas: pd.DataFrame, filtros: dict[str, object]) -> pd.DataFrame:
    inicio, fim = filtros["periodo"]
    linhas = filtros["linhas"]

    return paradas[
        (paradas["stop_start"].dt.date >= inicio)
        & (paradas["stop_start"].dt.date <= fim)
        & (paradas["line"].astype(str).isin(linhas))
    ]


def mostrar_kpis(kpis: dict[str, float | int]) -> None:
    colunas = st.columns(4)
    colunas[0].metric("FPY", formatar_percentual(kpis["fpy"]))
    colunas[1].metric("PPM", formatar_numero(kpis["ppm"]))
    colunas[2].metric("Yield Final", formatar_percentual(kpis["rendimento_final"]))
    colunas[3].metric("UPH", f"{kpis['uph']:.1f}")

    colunas = st.columns(4)
    colunas[0].metric("Tentativas", formatar_numero(kpis["total_tentativas"]))
    colunas[1].metric("Seriais", formatar_numero(kpis["total_seriais"]))
    colunas[2].metric("Rework", formatar_percentual(kpis["taxa_retrabalho"]))
    colunas[3].metric("Scrap", formatar_percentual(kpis["taxa_sucata"]))

    colunas = st.columns(3)
    colunas[0].metric("Downtime", f"{kpis['parada_min']:.0f} min")
    colunas[1].metric("Disponibilidade", formatar_percentual(kpis["disponibilidade"]))
    colunas[2].metric("Horas Planejadas", f"{kpis['horas_planejadas']:.1f} h")


def mostrar_pareto(gravacoes: pd.DataFrame, coluna: str, rotulo: str) -> None:
    pareto = montar_pareto_defeitos(gravacoes, coluna)
    if pareto.empty:
        st.info("Não há falhas no recorte filtrado.")
        return

    figura = go.Figure()
    figura.add_bar(
        x=pareto[coluna],
        y=pareto["quantidade"],
        name="Falhas",
        marker_color="#2f5f8f",
    )
    figura.add_scatter(
        x=pareto[coluna],
        y=pareto["percentual_acumulado"] * 100,
        name="% acumulado",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="#c74343", width=3),
    )
    figura.add_hline(
        y=80,
        line_dash="dash",
        line_color="#7a7a7a",
        yref="y2",
    )
    figura.update_layout(
        xaxis_title=rotulo,
        yaxis_title="Quantidade de falhas",
        yaxis2=dict(title="% acumulado", overlaying="y", side="right", range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(figura, width="stretch")

    maior_defeito = pareto.iloc[0]
    st.success(
        f"Maior item: {maior_defeito[coluna]} com "
        f"{maior_defeito['quantidade']} falhas "
        f"({maior_defeito['percentual'] * 100:.1f}% do total filtrado)."
    )
    st.dataframe(
        pareto.assign(
            percentual=lambda dados: (dados["percentual"] * 100).round(2),
            percentual_acumulado=lambda dados: (dados["percentual_acumulado"] * 100).round(2),
        ),
        width="stretch",
        hide_index=True,
    )


def mostrar_jig_etapa(gravacoes: pd.DataFrame) -> None:
    matriz = montar_matriz_jig_etapa(gravacoes)
    if matriz.empty:
        st.info("Não há falhas no recorte filtrado.")
        return

    figura = px.imshow(
        matriz,
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels=dict(x="Etapa com falha", y="Jig", color="Falhas"),
    )
    figura.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(figura, width="stretch")

    ranking = montar_ranking_jig_etapa(gravacoes)
    st.write("Combinações com mais falhas")
    st.dataframe(
        ranking.head(20),
        width="stretch",
        hide_index=True,
    )


def adicionar_paradas_linha(figura: go.Figure, paradas: pd.DataFrame) -> None:
    if paradas.empty:
        return

    for _, parada in paradas.iterrows():
        figura.add_vrect(
            x0=parada["stop_start"],
            x1=parada["stop_end"],
            fillcolor="#8a8a8a",
            opacity=0.18,
            line_width=0,
            annotation_text=parada["line"],
            annotation_position="top left",
        )


def mostrar_falhas_tempo(gravacoes: pd.DataFrame, paradas: pd.DataFrame) -> None:
    resumo = montar_falhas_por_hora(gravacoes)
    if resumo.empty:
        st.info("Não há registros no recorte filtrado.")
        return

    modo = st.radio(
        "Visualização",
        ["Falhas por hora", "Taxa de falha", "Falhas por erro"],
        horizontal=True,
    )

    if modo == "Falhas por hora":
        figura = px.bar(
            resumo,
            x="hora",
            y="falhas",
            labels={"hora": "Hora", "falhas": "Falhas"},
            color_discrete_sequence=["#2f5f8f"],
        )
    elif modo == "Taxa de falha":
        dados_taxa = resumo.assign(taxa_falha_pct=resumo["taxa_falha"] * 100)
        figura = px.line(
            dados_taxa,
            x="hora",
            y="taxa_falha_pct",
            markers=True,
            labels={"hora": "Hora", "taxa_falha_pct": "Taxa de falha (%)"},
            color_discrete_sequence=["#c74343"],
        )
    else:
        falhas_erro = montar_falhas_por_hora_erro(gravacoes)
        if falhas_erro.empty:
            st.info("Não há falhas com código de erro no recorte filtrado.")
            return

        principais_erros = falhas_erro.groupby("error_code")["falhas"].sum().nlargest(8).index
        falhas_erro = falhas_erro[falhas_erro["error_code"].isin(principais_erros)]
        figura = px.bar(
            falhas_erro,
            x="hora",
            y="falhas",
            color="error_code",
            labels={"hora": "Hora", "falhas": "Falhas", "error_code": "Erro"},
        )

    adicionar_paradas_linha(figura, paradas)
    figura.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(figura, width="stretch")

    st.write("Paradas de linha no recorte")
    if paradas.empty:
        st.info("Nenhuma parada de linha encontrada para os filtros atuais.")
    else:
        st.dataframe(
            paradas.sort_values("stop_start"),
            width="stretch",
            hide_index=True,
        )


def mostrar_cycle_time(gravacoes: pd.DataFrame) -> None:
    resumo = montar_resumo_cycle_time(gravacoes)
    if resumo.empty:
        st.info("Não há dados de cycle time no recorte filtrado.")
        return

    gargalo = resumo.iloc[0]
    st.success(
        f"Gargalo médio: {gargalo['etapa']} com média de "
        f"{gargalo['media_s']:.1f}s e p95 de {gargalo['p95_s']:.1f}s."
    )

    figura = px.bar(
        resumo.sort_values("media_s", ascending=True),
        x="media_s",
        y="etapa",
        orientation="h",
        error_x="p95_s",
        labels={"media_s": "Média (s)", "etapa": "Etapa", "p95_s": "P95 (s)"},
        color="media_s",
        color_continuous_scale="Blues",
    )
    figura.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(figura, width="stretch")

    colunas = st.columns(2)
    with colunas[0]:
        st.write("Resumo por etapa")
        st.dataframe(
            resumo.assign(
                media_s=lambda dados: dados["media_s"].round(1),
                mediana_s=lambda dados: dados["mediana_s"].round(1),
                p95_s=lambda dados: dados["p95_s"].round(1),
                max_s=lambda dados: dados["max_s"].round(1),
            ),
            width="stretch",
            hide_index=True,
        )

    with colunas[1]:
        st.write("Distribuição do tempo total")
        figura_hist = px.histogram(
            gravacoes,
            x="total_cycle_s",
            nbins=40,
            labels={"total_cycle_s": "Tempo total (s)"},
            color_discrete_sequence=["#2f5f8f"],
        )
        figura_hist.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(figura_hist, width="stretch")

    outliers = montar_outliers_cycle_time(gravacoes)
    st.write("Testes mais lentos")
    st.dataframe(outliers.head(50), width="stretch", hide_index=True)


def mostrar_yield_rework_scrap(gravacoes: pd.DataFrame) -> None:
    dimensoes = {
        "Linha": "line",
        "Estação": "station",
        "Jig": "jig_id",
        "Modelo": "model",
        "Firmware": "firmware_version",
        "Turno": "shift",
    }
    rotulo_dimensao = st.selectbox("Agrupar por", list(dimensoes.keys()))
    dimensao = dimensoes[rotulo_dimensao]

    resumo = montar_yield_por_dimensao(gravacoes, dimensao)
    if resumo.empty:
        st.info("Não há dados no recorte filtrado.")
        return

    resumo_grafico = resumo.assign(
        fpy_pct=resumo["fpy"] * 100,
        yield_final_pct=resumo["yield_final"] * 100,
        taxa_rework_pct=resumo["taxa_rework"] * 100,
        taxa_scrap_pct=resumo["taxa_scrap"] * 100,
    )

    colunas = st.columns(2)
    with colunas[0]:
        figura_fpy = px.bar(
            resumo_grafico,
            x=dimensao,
            y="fpy_pct",
            labels={dimensao: rotulo_dimensao, "fpy_pct": "FPY (%)"},
            color="fpy_pct",
            color_continuous_scale="RdYlGn",
        )
        figura_fpy.update_layout(coloraxis_showscale=False, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(figura_fpy, width="stretch")

    with colunas[1]:
        figura_taxas = px.bar(
            resumo_grafico,
            x=dimensao,
            y=["taxa_rework_pct", "taxa_scrap_pct"],
            barmode="group",
            labels={
                dimensao: rotulo_dimensao,
                "value": "Taxa (%)",
                "variable": "Indicador",
            },
        )
        figura_taxas.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(figura_taxas, width="stretch")

    tabela = resumo_grafico[
        [
            dimensao,
            "seriais",
            "tentativas",
            "fpy_pct",
            "yield_final_pct",
            "taxa_rework_pct",
            "taxa_scrap_pct",
        ]
    ].rename(
        columns={
            "fpy_pct": "fpy_%",
            "yield_final_pct": "yield_final_%",
            "taxa_rework_pct": "rework_%",
            "taxa_scrap_pct": "scrap_%",
        }
    )
    st.write("Resumo por dimensão")
    st.dataframe(
        tabela.round(2),
        width="stretch",
        hide_index=True,
    )

    rework_scrap = montar_rework_scrap_por_erro(gravacoes)
    st.write("Defeitos que mais geram rework e scrap")
    if rework_scrap.empty:
        st.info("Não há falhas com código de erro no recorte filtrado.")
    else:
        figura_erros = px.bar(
            rework_scrap.head(15),
            x="error_code",
            y=["rework", "scrap"],
            barmode="group",
            labels={"error_code": "Erro", "value": "Tentativas", "variable": "Disposition"},
        )
        figura_erros.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(figura_erros, width="stretch")
        st.dataframe(rework_scrap, width="stretch", hide_index=True)


def mostrar_auditoria(gravacoes: pd.DataFrame) -> None:
    resumo = montar_resumo_auditoria(gravacoes)
    macs_duplicados = montar_macs_duplicados(gravacoes)
    tentativas_serial = montar_tentativas_por_serial(gravacoes)

    colunas = st.columns(4)
    colunas[0].metric("Falhas", formatar_numero(resumo["falhas"]))
    colunas[1].metric("Scrap", formatar_numero(resumo["scrap"]))
    colunas[2].metric("Seriais com rework", formatar_numero(resumo["seriais_com_rework"]))
    colunas[3].metric("MACs duplicados", formatar_numero(resumo["macs_duplicados"]))

    st.divider()
    subtabs = st.tabs(["Registros", "MAC duplicado", "Seriais regravados"])

    with subtabs[0]:
        colunas_padrao = [
            "timestamp",
            "line",
            "station",
            "jig_id",
            "operator",
            "model",
            "firmware_version",
            "serial_number",
            "mac_address",
            "attempt",
            "result",
            "failed_step",
            "error_code",
            "disposition",
            "total_cycle_s",
        ]
        colunas_disponiveis = gravacoes.columns.tolist()
        colunas_escolhidas = st.multiselect(
            "Colunas da tabela",
            colunas_disponiveis,
            default=[coluna for coluna in colunas_padrao if coluna in colunas_disponiveis],
        )
        if not colunas_escolhidas:
            st.warning("Escolha pelo menos uma coluna para exibir.")
        else:
            tabela = gravacoes[colunas_escolhidas].sort_values("timestamp")
            st.dataframe(tabela, width="stretch", hide_index=True)

            csv = tabela.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Baixar CSV filtrado",
                data=csv,
                file_name="auditoria_filtrada.csv",
                mime="text/csv",
            )

    with subtabs[1]:
        st.write("MACs associados a mais de um serial diferente")
        if macs_duplicados.empty:
            st.success("Nenhum MAC duplicado encontrado no recorte filtrado.")
        else:
            st.dataframe(macs_duplicados, width="stretch", hide_index=True)

    with subtabs[2]:
        st.write("Seriais que passaram por rework")
        if tentativas_serial.empty:
            st.success("Nenhum serial regravado encontrado no recorte filtrado.")
        else:
            st.dataframe(tentativas_serial, width="stretch", hide_index=True)


def mostrar_processo() -> None:
    subtabs = st.tabs(["BPMN", "PDD"])

    with subtabs[0]:
        st.write("Fluxo as-is do teste de gravação")
        st.image(BPMN_IMAGEM, caption="BPMN do processo de gravação e validação", width="stretch")

    with subtabs[1]:
        for secao in PDD_SECOES:
            st.markdown(f"#### {secao['titulo']}")
            for item in secao["itens"]:
                st.markdown(f"- {item}")


def mostrar_relatorio(gravacoes: pd.DataFrame, paradas: pd.DataFrame, filtros: dict[str, object]) -> None:
    achados = montar_achados(gravacoes, paradas)
    relatorio_html = gerar_relatorio_html(gravacoes, paradas, filtros)
    relatorio_pdf = gerar_relatorio_pdf(gravacoes, paradas, filtros)

    st.write("Achados que serão incluídos no relatório")
    if not achados:
        st.info("Nenhum achado encontrado para o recorte filtrado.")
    else:
        for achado in achados:
            with st.container(border=True):
                st.markdown(f"**{achado['titulo']}**")
                st.write(achado["descricao"])
                st.caption(f"Como reproduzir: {achado['reproducao']}")

    colunas = st.columns(2)
    colunas[0].download_button(
        "Baixar relatório HTML",
        data=relatorio_html.encode("utf-8"),
        file_name="relatorio_anomalias_setupbox.html",
        mime="text/html",
    )
    colunas[1].download_button(
        "Baixar relatório PDF",
        data=relatorio_pdf,
        file_name="relatorio_anomalias_setupbox.pdf",
        mime="application/pdf",
    )

    #with st.expander("Prévia do HTML gerado"):
        #st.code(relatorio_html[:8000], language="html")


def principal() -> None:
    st.title("Dashboard de Anomalias no Teste de Gravação de Setupbox")
    st.caption("Tarefa Assíncrona da Disciplina de Técnicas de Hiperautomação")

    st.sidebar.header("Filtros")
    caminho_dados = Path(ARQUIVO_DADOS)
    if not caminho_dados.exists():
        st.error(f"Arquivo `{ARQUIVO_DADOS}` não encontrado na pasta do projeto.")
        st.stop()

    gravacoes, paradas, dicionario = carregar_dados(str(caminho_dados))
    gravacoes_filtradas, filtros = filtrar_gravacoes(gravacoes)
    paradas_filtradas = filtrar_paradas(paradas, filtros)
    kpis = calcular_kpis_basicos(gravacoes_filtradas, paradas_filtradas)

    abas = st.tabs(
        [
            "Visão Geral",
            "Pareto",
            "Jig x Etapa",
            "Falhas no Tempo",
            "Cycle Time",
            "Yield / Rework / Scrap",
            "Auditoria",
            "Processo",
            "Relatório",
        ]
    )

    with abas[0]:
        st.subheader("Visão Geral")
        mostrar_kpis(kpis)

        st.divider()
        st.write("Resumo do recorte filtrado")

        colunas = st.columns(3)
        colunas[0].dataframe(
            gravacoes_filtradas["result"].value_counts().rename_axis("Resultado").reset_index(name="Tentativas"),
            width="stretch",
            hide_index=True,
        )
        colunas[1].dataframe(
            gravacoes_filtradas["disposition"].value_counts().rename_axis("Disposition").reset_index(name="Tentativas"),
            width="stretch",
            hide_index=True,
        )
        colunas[2].dataframe(
            gravacoes_filtradas["line"].value_counts().rename_axis("Linha").reset_index(name="Tentativas"),
            width="stretch",
            hide_index=True,
        )

        st.write("Prévia dos registros")
        colunas_previas = [
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
            "disposition",
            "total_cycle_s",
        ]
        st.dataframe(
            gravacoes_filtradas[colunas_previas].head(200),
            width="stretch",
            hide_index=True,
        )

    with abas[1]:
        st.subheader("Pareto de Defeitos")
        opcao_pareto = st.radio(
            "Agrupar por",
            ["error_code", "failed_step"],
            horizontal=True,
        )
        rotulo = "Código de erro" if opcao_pareto == "error_code" else "Etapa com falha"
        mostrar_pareto(gravacoes_filtradas, opcao_pareto, rotulo)

    with abas[2]:
        st.subheader("Jig x Etapa")
        mostrar_jig_etapa(gravacoes_filtradas)

    with abas[3]:
        st.subheader("Falhas ao Longo do Tempo")
        mostrar_falhas_tempo(gravacoes_filtradas, paradas_filtradas)

    with abas[4]:
        st.subheader("Cycle Time")
        mostrar_cycle_time(gravacoes_filtradas)

    with abas[5]:
        st.subheader("Yield, Rework e Scrap")
        mostrar_yield_rework_scrap(gravacoes_filtradas)

    with abas[6]:
        st.subheader("Auditoria")
        mostrar_auditoria(gravacoes_filtradas)

    with abas[7]:
        st.subheader("BPMN e PDD")
        mostrar_processo()

    with abas[8]:
        st.subheader("Relatório Exportável")
        mostrar_relatorio(gravacoes_filtradas, paradas_filtradas, filtros)


if __name__ == "__main__":
    principal()
