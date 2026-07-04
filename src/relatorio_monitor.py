from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd


def gerar_relatorio_monitor(
    alertas: pd.DataFrame,
    auditoria: pd.DataFrame,
    revisoes: pd.DataFrame,
    avaliacao: pd.DataFrame,
) -> str:
    total_alertas = len(alertas)
    total_janelas = len(auditoria)
    pendentes = len(revisoes)

    severidades = _tabela_contagem(alertas, "severidade")
    tipos = _tabela_contagem(alertas, "tipo_alerta")

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Relatório do Monitor de Anomalias</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #1f2d3d; margin: 36px; line-height: 1.45; }}
    h1, h2 {{ color: #1f2d3d; }}
    .grade {{ display: grid; grid-template-columns: repeat(3, minmax(150px, 1fr)); gap: 12px; }}
    .kpi {{ border: 1px solid #d5dde5; border-radius: 8px; padding: 12px; background: #f8fafc; }}
    .kpi strong {{ display: block; font-size: 26px; margin-top: 6px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 10px 0 24px 0; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #d8e0e8; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #eef3f7; }}
  </style>
</head>
<body>
  <h1>Relatório do Monitor de Anomalias</h1>
  <p>Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}.</p>

  <div class="grade">
    <div class="kpi">Janelas processadas<strong>{total_janelas}</strong></div>
    <div class="kpi">Alertas gerados<strong>{total_alertas}</strong></div>
    <div class="kpi">Pendências HITL<strong>{pendentes}</strong></div>
  </div>

  <h2>Alertas por severidade</h2>
  {severidades}

  <h2>Alertas por tipo</h2>
  {tipos}

  <h2>Ultimos alertas</h2>
  {_html_tabela(alertas.tail(30))}

  <h2>Revisão humana pendente</h2>
  {_html_tabela(revisoes)}

  <h2>Avaliação do monitor</h2>
  {_html_tabela(avaliacao)}

  <h2>Auditoria das janelas</h2>
  {_html_tabela(auditoria.tail(50))}
</body>
</html>"""


def _tabela_contagem(dados: pd.DataFrame, coluna: str) -> str:
    if dados.empty or coluna not in dados:
        return "<p>Nenhum alerta gerado.</p>"
    tabela = dados[coluna].value_counts().rename_axis(coluna).reset_index(name="quantidade")
    return _html_tabela(tabela)


def _html_tabela(dados: pd.DataFrame) -> str:
    if dados.empty:
        return "<p>Nenhum registro.</p>"
    return dados.map(_limpar).to_html(index=False, border=0, escape=False)


def _limpar(valor: object) -> str:
    texto = "" if pd.isna(valor) else str(valor)
    if len(texto) > 240:
        texto = texto[:237] + "..."
    return escape(texto)
