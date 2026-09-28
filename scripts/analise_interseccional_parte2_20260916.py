# -*- coding: utf-8 -*-
"""
analise_interseccional_parte2_20260916.py

Continuacao de analise_interseccional_20260916.py, dois pontos pedidos pelo autor:
  (a) bootstrap do RERI tambem para IA grave (pulado na primeira rodada por custo
      computacional -- so' havia ponto estimado).
  (b) estratificacao regional do par raca x sexo (o unico com interacao aditiva
      confirmada na rodada nacional), para testar a dimensao territorial do
      candidato #1 (raca-genero-territorio).

Reusa rr_celulas/bootstrap_reri do script anterior -- mesma logica de peso
(var_weights) e cluster-robusto por UPA, nao um pipeline novo.

Saida: resultados/interseccional_2023_parte2.csv
"""
import warnings
warnings.filterwarnings("ignore")

import gc
import csv

import numpy as np
from pathlib import Path

from analise_bivariada_e_regressao_v2 import ler_microdados, preparar
from analise_interseccional_20260916 import rr_celulas, bootstrap_reri
from processar_uf_determinantes import REGIAO

BASE = Path(__file__).parent
OUT = BASE / "resultados" / "interseccional_2023_parte2.csv"

CAMPOS = ["parte", "par", "regiao", "desfecho", "prev_00", "prev_10", "prev_01", "prev_11",
          "rr10", "rr01", "rr11", "reri", "razao_razoes", "p_c11",
          "reri_ic95_low", "reri_ic95_high", "n_boot_validas", "n_total_celula"]


def escrever_linha(linha, primeira):
    modo = "w" if primeira else "a"
    with open(OUT, modo, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if primeira:
            w.writeheader()
        w.writerow(linha)


def main():
    df = ler_microdados()
    resp = preparar(df)
    del df
    gc.collect()
    resp["regiao"] = resp["UF"].str.strip().map(REGIAO)

    primeira = True

    # ---------------- (a) bootstrap do RERI para IA grave, 3 pares nacionais ----------------
    pares = [
        ("negra", "mulher", "Cor/raça (preta+parda) × Sexo (mulher)"),
        ("negra", "sem_fund", "Cor/raça (preta+parda) × Instrução (sem instrução/fund. incompleto)"),
        ("negra", "renda_q1", "Cor/raça (preta+parda) × Renda (até 1/4 SM)"),
    ]
    for v1, v2, rotulo in pares:
        desfecho = "ia_grave"
        print(f"\n=== (a) {rotulo} — {desfecho}, Brasil ===", flush=True)
        res, sub = rr_celulas(resp, v1, v2, desfecho)
        print(f"  RR só {v1}={res['rr10']:.3f} | RR só {v2}={res['rr01']:.3f} | "
              f"RR ambos={res['rr11']:.3f} | RERI ponto={res['reri']:+.3f}", flush=True)
        lo, hi, n_ok = bootstrap_reri(sub, desfecho, n_boot=300)
        print(f"  IC95% bootstrap do RERI: [{lo:+.3f}, {hi:+.3f}]  contém zero: {lo < 0 < hi}",
              flush=True)
        linha = {"parte": "a_nacional_grave", "par": rotulo, "regiao": "Brasil",
                 "desfecho": desfecho,
                 **{k: v for k, v in res.items() if not k.startswith("n_")},
                 "reri_ic95_low": lo, "reri_ic95_high": hi, "n_boot_validas": n_ok,
                 "n_total_celula": len(sub)}
        escrever_linha(linha, primeira)
        primeira = False
        del sub, res
        gc.collect()

    # ---------------- (b) raça × sexo, estratificado por região ----------------
    v1, v2, rotulo = "negra", "mulher", "Cor/raça (preta+parda) × Sexo (mulher)"
    for regiao in ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]:
        sub_regiao = resp[resp["regiao"] == regiao]
        for desfecho in ["ia_total", "ia_grave"]:
            print(f"\n=== (b) {rotulo} — {desfecho}, {regiao} (n={len(sub_regiao)}) ===",
                  flush=True)
            try:
                res, sub = rr_celulas(sub_regiao, v1, v2, desfecho)
            except Exception as e:
                print(f"  falhou: {e}", flush=True)
                continue
            print(f"  Prevalência: ref={res['prev_00']:.1f}% | só negra={res['prev_10']:.1f}% | "
                  f"só mulher={res['prev_01']:.1f}% | ambos={res['prev_11']:.1f}%", flush=True)
            print(f"  RR negra={res['rr10']:.3f} | RR mulher={res['rr01']:.3f} | "
                  f"RR ambos={res['rr11']:.3f} | RERI ponto={res['reri']:+.3f}", flush=True)
            lo, hi, n_ok = bootstrap_reri(sub, desfecho, n_boot=300)
            print(f"  IC95% bootstrap do RERI: [{lo:+.3f}, {hi:+.3f}]  contém zero: {lo < 0 < hi}",
                  flush=True)
            linha = {"parte": "b_regional", "par": rotulo, "regiao": regiao,
                     "desfecho": desfecho,
                     **{k: v for k, v in res.items() if not k.startswith("n_")},
                     "reri_ic95_low": lo, "reri_ic95_high": hi, "n_boot_validas": n_ok,
                     "n_total_celula": len(sub)}
            escrever_linha(linha, primeira)
            primeira = False
            del sub, res
            gc.collect()

    print(f"\nSalvo: {OUT}", flush=True)


if __name__ == "__main__":
    main()
