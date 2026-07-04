from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.alertas import alertas_para_dataframe, criar_alerta, montar_revisoes
from src.avaliacao import avaliar_alertas
from src.monitoramento import carregar_logs, filtrar_paradas_janela, iterar_janelas, recorte_baseline
from src.regras import ConfigRegras, avaliar_regras, montar_baseline
from src.relatorio_monitor import gerar_relatorio_monitor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor de anomalias do teste de gravação de setupbox.")
    parser.add_argument("--input", default="recording_test_setupbox.xlsx", help="Arquivo ou pasta de logs.")
    parser.add_argument("--output", default="saida_monitor", help="Pasta de saída do monitor.")
    parser.add_argument("--window-minutes", type=int, default=60, help="Tamanho da janela movel em minutos.")
    parser.add_argument("--step-minutes", type=int, default=15, help="Passo entre janelas em minutos.")
    parser.add_argument("--baseline-hours", type=int, default=12, help="Horas iniciais usadas como baseline.")
    parser.add_argument("--min-consecutive", type=int, default=2, help="Janelas consecutivas para confirmar anomalia sistemática.")
    parser.add_argument("--gabarito", default="", help="CSV opcional com incidentes reais para avaliação.")
    return parser.parse_args()


def executar_monitor(args: argparse.Namespace) -> dict[str, Path | int]:
    saida = Path(args.output)
    saida.mkdir(parents=True, exist_ok=True)

    gravacoes, paradas = carregar_logs(args.input)
    baseline_dados = recorte_baseline(gravacoes, args.baseline_hours)
    baseline = montar_baseline(baseline_dados)
    inicio_monitoramento = gravacoes["timestamp"].min() + pd.Timedelta(hours=args.baseline_hours)

    config = ConfigRegras()
    estado_recorrencia: dict[str, int] = {}
    estado_ausencia: dict[str, int] = {}
    estado_emitido: dict[str, str] = {}
    alertas = []
    auditoria = []

    for inicio, fim, janela in iterar_janelas(
        gravacoes,
        minutos_janela=args.window_minutes,
        minutos_passo=args.step_minutes,
        inicio_monitoramento=inicio_monitoramento,
    ):
        historico = gravacoes[gravacoes["timestamp"] <= fim].copy()
        paradas_janela = filtrar_paradas_janela(paradas, inicio, fim)
        candidatos = avaliar_regras(janela, historico, baseline, config)
        chaves_ativas = set()
        alertas_janela = 0
        revisoes_janela = 0

        for candidato in candidatos:
            chave_estado = f"{candidato['tipo_alerta']}|{candidato['chave']}"
            chaves_ativas.add(chave_estado)
            estado_recorrencia[chave_estado] = estado_recorrencia.get(chave_estado, 0) + 1
            estado_ausencia[chave_estado] = 0
            recorrencias = estado_recorrencia[chave_estado]
            exige_recorrencia = bool(candidato.get("exige_recorrencia", True))

            confirmado = (not exige_recorrencia) or recorrencias >= args.min_consecutive
            severidade = str(candidato.get("severidade", "MEDIA"))
            hitl = severidade in {"ALTA", "CRITICA"} or not confirmado
            status = "ALERTA_CONFIRMADO" if confirmado else "REVISAO_AMBIGUA"
            severidade_final = severidade if confirmado else "BAIXA"
            emissao = "CONFIRMADO" if confirmado else "AMBIGUO"

            if estado_emitido.get(chave_estado) == "CONFIRMADO":
                continue
            if estado_emitido.get(chave_estado) == "AMBIGUO" and emissao == "AMBIGUO":
                continue

            alerta = criar_alerta(
                candidato=candidato,
                window_start=inicio,
                window_end=fim,
                created_at=fim,
                status=status,
                hitl_required=hitl,
                severidade=severidade_final,
            )
            alertas.append(alerta)
            estado_emitido[chave_estado] = emissao
            alertas_janela += 1
            revisoes_janela += int(hitl)

        for chave in list(estado_recorrencia):
            if chave not in chaves_ativas:
                estado_recorrencia[chave] = 0
                estado_ausencia[chave] = estado_ausencia.get(chave, 0) + 1
                if estado_ausencia[chave] >= args.min_consecutive:
                    estado_emitido.pop(chave, None)
                    estado_ausencia.pop(chave, None)

        auditoria.append(
            {
                "window_start": inicio.isoformat(),
                "window_end": fim.isoformat(),
                "registros": len(janela),
                "falhas": int((janela["result"] == "FAIL").sum()) if not janela.empty else 0,
                "taxa_falha": float((janela["result"] == "FAIL").mean()) if not janela.empty else 0,
                "paradas_relacionadas": len(paradas_janela),
                "candidatos_regras": len(candidatos),
                "alertas_emitidos": alertas_janela,
                "revisoes_hitl": revisoes_janela,
            }
        )

    alertas_df = alertas_para_dataframe(alertas)
    revisoes_df = montar_revisoes(alertas)
    auditoria_df = pd.DataFrame(auditoria)
    avaliacao_df, pareamentos_df = avaliar_alertas(alertas_df, args.gabarito or None)
    relatorio_html = gerar_relatorio_monitor(alertas_df, auditoria_df, revisoes_df, avaliacao_df)

    caminhos = {
        "alertas": saida / "alertas.csv",
        "auditoria": saida / "auditoria.csv",
        "revisao": saida / "revisao_humana.csv",
        "avaliacao": saida / "avaliacao.csv",
        "pareamentos": saida / "pareamentos_gabarito.csv",
        "relatorio": saida / "relatorio_monitor.html",
    }

    alertas_df.to_csv(caminhos["alertas"], index=False, encoding="utf-8-sig")
    auditoria_df.to_csv(caminhos["auditoria"], index=False, encoding="utf-8-sig")
    revisoes_df.to_csv(caminhos["revisao"], index=False, encoding="utf-8-sig")
    avaliacao_df.to_csv(caminhos["avaliacao"], index=False, encoding="utf-8-sig")
    pareamentos_df.to_csv(caminhos["pareamentos"], index=False, encoding="utf-8-sig")
    caminhos["relatorio"].write_text(relatorio_html, encoding="utf-8")

    return {
        **caminhos,
        "total_alertas": len(alertas_df),
        "total_janelas": len(auditoria_df),
        "total_revisoes": len(revisoes_df),
    }


def main() -> None:
    resultado = executar_monitor(parse_args())
    print("Monitor executado com sucesso.")
    print(f"Janelas processadas: {resultado['total_janelas']}")
    print(f"Alertas gerados: {resultado['total_alertas']}")
    print(f"Revisões HITL pendentes: {resultado['total_revisoes']}")
    print(f"Alertas: {resultado['alertas']}")
    print(f"Auditoria: {resultado['auditoria']}")
    print(f"Relatório: {resultado['relatorio']}")


if __name__ == "__main__":
    main()
