from base64 import b64encode
from io import BytesIO
from pathlib import Path
import textwrap
from datetime import datetime
from html import escape

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from src.metricas import (
    calcular_kpis_basicos,
    montar_falhas_por_hora,
    montar_macs_duplicados,
    montar_pareto_defeitos,
    montar_ranking_jig_etapa,
    montar_rework_scrap_por_erro,
    montar_resumo_cycle_time,
)
from src.processo import BPMN_IMAGEM, PDD_SECOES


COR_TEXTO = "#1f2d3d"
COR_SECUNDARIA = "#516070"
COR_LINHA = "#d5dde5"
COR_CARD = "#f8fafc"


def caminho_bpmn() -> Path:
    return Path(BPMN_IMAGEM)


def percentual(valor: float) -> str:
    return f"{valor * 100:.2f}%"


def numero(valor: float | int) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def tabela_html(dados: pd.DataFrame, max_linhas: int = 20) -> str:
    if dados.empty:
        return "<p>Nenhum registro encontrado.</p>"
    return dados.head(max_linhas).to_html(index=False, border=0, classes="tabela")


def imagem_bpmn_html() -> str:
    caminho = caminho_bpmn()
    if not caminho.exists():
        return "<p>Imagem BPMN não encontrada.</p>"

    conteudo = b64encode(caminho.read_bytes()).decode("ascii")
    return f"<img src='data:image/png;base64,{conteudo}' alt='BPMN do processo de gravação de setupbox'>"


def filtro_texto(filtros: dict[str, object]) -> str:
    linhas = []
    for chave, valor in filtros.items():
        if isinstance(valor, list):
            exibido = ", ".join(map(str, valor[:8]))
            if len(valor) > 8:
                exibido += f" ... (+{len(valor) - 8})"
        else:
            exibido = str(valor)
        linhas.append(f"<li><strong>{escape(chave)}:</strong> {escape(exibido)}</li>")
    return "\n".join(linhas)


def montar_achados(gravacoes: pd.DataFrame, paradas: pd.DataFrame) -> list[dict[str, str]]:
    pareto = montar_pareto_defeitos(gravacoes)
    ranking = montar_ranking_jig_etapa(gravacoes)
    falhas_hora = montar_falhas_por_hora(gravacoes)
    cycle = montar_resumo_cycle_time(gravacoes)
    rework_scrap = montar_rework_scrap_por_erro(gravacoes)
    macs = montar_macs_duplicados(gravacoes)

    achados = []
    if not pareto.empty:
        maior = pareto.iloc[0]
        achados.append(
            {
                "titulo": "Maior defeito no Pareto",
                "descricao": f"{maior['error_code']} concentra {int(maior['quantidade'])} falhas, "
                f"representando {maior['percentual'] * 100:.1f}% das falhas filtradas.",
                "reproducao": "Aba Pareto > agrupar por error_code.",
            }
        )

    if not ranking.empty:
        item = ranking.iloc[0]
        achados.append(
            {
                "titulo": "Equipamento crônico",
                "descricao": f"O jig {item['jig_id']} aparece no topo com etapa {item['failed_step']}, "
                f"erro {item['error_code']} e {int(item['quantidade'])} falhas.",
                "reproducao": "Aba Jig x Etapa > ranking das combinações com mais falhas.",
            }
        )

    if not falhas_hora.empty:
        pico = falhas_hora.sort_values("falhas", ascending=False).iloc[0]
        achados.append(
            {
                "titulo": "Pico de falhas no tempo",
                "descricao": f"O maior pico ocorreu em {pico['hora']}, com {int(pico['falhas'])} falhas "
                f"em {int(pico['tentativas'])} tentativas.",
                "reproducao": "Aba Falhas no Tempo > visualização Falhas por hora.",
            }
        )

    if not cycle.empty:
        gargalo = cycle.iloc[0]
        achados.append(
            {
                "titulo": "Gargalo de cycle time",
                "descricao": f"A etapa {gargalo['etapa']} tem a maior média de cycle time "
                f"({gargalo['media_s']:.1f}s) e p95 de {gargalo['p95_s']:.1f}s.",
                "reproducao": "Aba Cycle Time > resumo por etapa.",
            }
        )

    if not rework_scrap.empty:
        pior_scrap = rework_scrap.sort_values("scrap", ascending=False).iloc[0]
        achados.append(
            {
                "titulo": "Defeito com maior scrap",
                "descricao": f"O erro {pior_scrap['error_code']} gerou {int(pior_scrap['scrap'])} scraps "
                f"e {int(pior_scrap['rework'])} reworks.",
                "reproducao": "Aba Yield / Rework / Scrap > defeitos que mais geram rework e scrap.",
            }
        )

    if not macs.empty:
        pior_mac = macs.iloc[0]
        achados.append(
            {
                "titulo": "Integridade de MAC",
                "descricao": f"O MAC {pior_mac['mac_address']} aparece associado a "
                f"{int(pior_mac['seriais_distintos'])} seriais diferentes.",
                "reproducao": "Aba Auditoria > MAC duplicado.",
            }
        )

    if not paradas.empty:
        maior_parada = paradas.sort_values("duration_min", ascending=False).iloc[0]
        achados.append(
            {
                "titulo": "Maior parada de linha no recorte",
                "descricao": f"A maior parada foi na linha {maior_parada['line']}, de "
                f"{maior_parada['stop_start']} até {maior_parada['stop_end']}, "
                f"com {maior_parada['duration_min']:.0f} minutos. Motivo: {maior_parada['reason']}.",
                "reproducao": "Aba Falhas no Tempo > tabela de paradas de linha no recorte.",
            }
        )

    return achados


def gerar_relatorio_html(
    gravacoes: pd.DataFrame,
    paradas: pd.DataFrame,
    filtros: dict[str, object],
) -> str:
    kpis = calcular_kpis_basicos(gravacoes, paradas)
    achados = montar_achados(gravacoes, paradas)
    pareto = montar_pareto_defeitos(gravacoes).copy()
    ranking = montar_ranking_jig_etapa(gravacoes).copy()
    macs = montar_macs_duplicados(gravacoes).copy()

    if not pareto.empty:
        pareto["percentual"] = (pareto["percentual"] * 100).round(2)
        pareto["percentual_acumulado"] = (pareto["percentual_acumulado"] * 100).round(2)

    pdd_html = []
    for secao in PDD_SECOES:
        itens = "".join(f"<li>{escape(item)}</li>" for item in secao["itens"])
        pdd_html.append(f"<h3>{escape(secao['titulo'])}</h3><ul>{itens}</ul>")

    achados_html = []
    for achado in achados:
        achados_html.append(
            "<div class='achado'>"
            f"<h3>{escape(achado['titulo'])}</h3>"
            f"<p>{escape(achado['descricao'])}</p>"
            f"<p><strong>Como reproduzir:</strong> {escape(achado['reproducao'])}</p>"
            "</div>"
        )

    return f"""
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Relatório de Anomalias - Setupbox</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #1f2d3d; margin: 36px; line-height: 1.45; }}
    h1, h2, h3 {{ color: #1f2d3d; }}
    .grade {{ display: grid; grid-template-columns: repeat(4, minmax(130px, 1fr)); gap: 12px; }}
    .kpi, .achado {{ border: 1px solid #d5dde5; border-radius: 8px; padding: 12px; background: #f8fafc; }}
    .kpi strong {{ display: block; font-size: 22px; margin-top: 6px; }}
    .tabela {{ border-collapse: collapse; width: 100%; margin: 10px 0 20px 0; font-size: 13px; }}
    .tabela th, .tabela td {{ border-bottom: 1px solid #d8e0e8; padding: 8px; text-align: left; }}
    .tabela th {{ background: #eef3f7; }}
    img {{ max-width: 100%; border: 1px solid #d5dde5; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>Relatório de Anomalias no Teste de Gravação de Setupbox</h1>
  <p>Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}.</p>

  <h2>Filtros aplicados</h2>
  <ul>{filtro_texto(filtros)}</ul>

  <h2>KPIs do recorte</h2>
  <div class="grade">
    <div class="kpi">FPY<strong>{percentual(kpis["fpy"])}</strong></div>
    <div class="kpi">PPM<strong>{numero(kpis["ppm"])}</strong></div>
    <div class="kpi">Yield final<strong>{percentual(kpis["rendimento_final"])}</strong></div>
    <div class="kpi">UPH<strong>{kpis["uph"]:.1f}</strong></div>
    <div class="kpi">Tentativas<strong>{numero(kpis["total_tentativas"])}</strong></div>
    <div class="kpi">Seriais<strong>{numero(kpis["total_seriais"])}</strong></div>
    <div class="kpi">Rework<strong>{percentual(kpis["taxa_retrabalho"])}</strong></div>
    <div class="kpi">Scrap<strong>{percentual(kpis["taxa_sucata"])}</strong></div>
  </div>

  <h2>Achados principais</h2>
  {''.join(achados_html)}

  <h2>Pareto de defeitos</h2>
  {tabela_html(pareto, 15)}

  <h2>Ranking jig x etapa</h2>
  {tabela_html(ranking, 20)}

  <h2>MACs duplicados</h2>
  {tabela_html(macs, 20)}

  <h2>BPMN</h2>
  {imagem_bpmn_html()}

  <h2>PDD</h2>
  {''.join(pdd_html)}
</body>
</html>
"""


def fonte(tamanho: int, negrito: bool = False) -> ImageFont.FreeTypeFont:
    nome = "DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf"
    caminhos = [
        Path("/usr/share/fonts/truetype/dejavu") / nome,
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for caminho in caminhos:
        if caminho.exists():
            return ImageFont.truetype(str(caminho), tamanho)
    return ImageFont.load_default()


def quebrar_texto(texto: str, largura: int = 92) -> list[str]:
    linhas = []
    for bloco in str(texto).splitlines() or [""]:
        linhas.extend(textwrap.wrap(bloco, width=largura) or [""])
    return linhas


def desenhar_linhas(
    draw: ImageDraw.ImageDraw,
    linhas: list[str],
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: str = COR_TEXTO,
    espacamento: int = 10,
) -> int:
    for linha in linhas:
        draw.text((x, y), linha, font=font, fill=fill)
        bbox = draw.textbbox((x, y), linha, font=font)
        y += bbox[3] - bbox[1] + espacamento
    return y


def nova_pagina() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    pagina = Image.new("RGB", (1240, 1754), "white")
    return pagina, ImageDraw.Draw(pagina)


def adicionar_pagina(paginas: list[Image.Image], pagina: Image.Image) -> None:
    paginas.append(pagina)


def gerar_relatorio_pdf(
    gravacoes: pd.DataFrame,
    paradas: pd.DataFrame,
    filtros: dict[str, object],
) -> bytes:
    kpis = calcular_kpis_basicos(gravacoes, paradas)
    achados = montar_achados(gravacoes, paradas)
    pareto = montar_pareto_defeitos(gravacoes).copy()
    ranking = montar_ranking_jig_etapa(gravacoes).copy()
    macs = montar_macs_duplicados(gravacoes).copy()

    titulo = fonte(34, True)
    subtitulo = fonte(24, True)
    normal = fonte(19)
    pequeno = fonte(16)
    paginas = []

    pagina, draw = nova_pagina()
    y = 70
    draw.text((70, y), "Relatório de Anomalias no Teste de Gravação de Setupbox", font=titulo, fill=COR_TEXTO)
    y += 52
    draw.text((70, y), f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", font=normal, fill=COR_SECUNDARIA)
    y += 55

    draw.text((70, y), "KPIs do recorte", font=subtitulo, fill=COR_TEXTO)
    y += 38
    kpi_linhas = [
        f"FPY: {percentual(kpis['fpy'])}",
        f"PPM: {numero(kpis['ppm'])}",
        f"Yield final: {percentual(kpis['rendimento_final'])}",
        f"UPH: {kpis['uph']:.1f}",
        f"Tentativas: {numero(kpis['total_tentativas'])}",
        f"Seriais: {numero(kpis['total_seriais'])}",
        f"Rework: {percentual(kpis['taxa_retrabalho'])}",
        f"Scrap: {percentual(kpis['taxa_sucata'])}",
    ]
    for indice, linha in enumerate(kpi_linhas):
        col = indice % 2
        row = indice // 2
        x = 70 + col * 520
        yy = y + row * 42
        draw.rounded_rectangle((x, yy, x + 470, yy + 34), radius=8, fill=COR_CARD, outline=COR_LINHA)
        draw.text((x + 12, yy + 7), linha, font=normal, fill=COR_TEXTO)
    y += 210

    draw.text((70, y), "Achados principais", font=subtitulo, fill=COR_TEXTO)
    y += 40
    for achado in achados:
        bloco = f"{achado['titulo']}: {achado['descricao']} Como reproduzir: {achado['reproducao']}"
        y = desenhar_linhas(draw, quebrar_texto("- " + bloco, 105), 90, y, pequeno, espacamento=8)
        y += 8
        if y > 1580:
            adicionar_pagina(paginas, pagina)
            pagina, draw = nova_pagina()
            y = 70

    adicionar_pagina(paginas, pagina)

    pagina, draw = nova_pagina()
    y = 70
    draw.text((70, y), "BPMN do processo", font=subtitulo, fill=COR_TEXTO)
    y += 45
    caminho = caminho_bpmn()
    if caminho.exists():
        bpmn = Image.open(caminho).convert("RGB")
        bpmn.thumbnail((1100, 760))
        pagina.paste(bpmn, (70, y))
        y += bpmn.height + 45
    else:
        y = desenhar_linhas(draw, ["Imagem BPMN não encontrada."], 70, y, normal)

    draw.text((70, y), "PDD", font=subtitulo, fill=COR_TEXTO)
    y += 42
    for secao in PDD_SECOES:
        if y > 1540:
            adicionar_pagina(paginas, pagina)
            pagina, draw = nova_pagina()
            y = 70
        draw.text((70, y), secao["titulo"], font=normal, fill=COR_TEXTO)
        y += 30
        for item in secao["itens"]:
            y = desenhar_linhas(draw, quebrar_texto("- " + item, 105), 90, y, pequeno, fill=COR_SECUNDARIA, espacamento=7)
        y += 14

    adicionar_pagina(paginas, pagina)

    pagina, draw = nova_pagina()
    y = 70
    draw.text((70, y), "Tabelas de apoio", font=subtitulo, fill=COR_TEXTO)
    y += 50
    tabelas = [
        ("Pareto de defeitos", pareto.head(10)),
        ("Ranking jig x etapa", ranking.head(10)),
        ("MACs duplicados", macs.head(10)),
    ]
    for nome, dados in tabelas:
        draw.text((70, y), nome, font=normal, fill=COR_TEXTO)
        y += 32
        if dados.empty:
            y = desenhar_linhas(draw, ["Nenhum registro encontrado."], 90, y, pequeno)
        else:
            for linha in dados.astype(str).head(10).to_dict("records"):
                texto = " | ".join(f"{chave}: {valor}" for chave, valor in linha.items())
                y = desenhar_linhas(draw, quebrar_texto(texto, 110), 90, y, pequeno, fill=COR_SECUNDARIA, espacamento=6)
                y += 5
                if y > 1580:
                    adicionar_pagina(paginas, pagina)
                    pagina, draw = nova_pagina()
                    y = 70
        y += 24

    adicionar_pagina(paginas, pagina)

    saida = BytesIO()
    paginas[0].save(saida, format="PDF", save_all=True, append_images=paginas[1:])
    return saida.getvalue()

