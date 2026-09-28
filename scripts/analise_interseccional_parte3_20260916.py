# -*- coding: utf-8 -*-
"""
analise_interseccional_parte3_20260916.py

Terceira rodada pedida pelo autor:
  (a) raça × situação domiciliar (rural/urbano) -- mesmo tratamento par a par
      das rodadas anteriores (RR das 4 células, RERI aditivo com IC95%
      bootstrap por conglomerado).
  (b) modelo conjunto: as quatro interações com raça (sexo, instrução, renda,
      rural) no MESMO modelo, mutuamente ajustadas -- testa se cada interação
      sobrevive quando as outras entram junto (elas são correlacionadas entre
      si: renda baixa, pouca instrução e área rural andam juntas).
  (c) gradiente de desvantagem acumulada: conta quantas das 4 dimensões
      (mulher, sem_fund, renda_q1, rural) cada domicílio acumula (0 a 4) e
      testa se a inclinação desse gradiente é diferente para domicílios
      negros vs. não negros -- é a pergunta "múltipla desvantagem" de forma
      direta, sem quebrar em pares.

(b) e (c) usam erro-padrão robusto agrupado por UPA (cluster-robust), que já
é uma inferência válida por si só -- não precisam de bootstrap adicional,
ao contrário do RERI em (a), que não tem erro-padrão fechado.

Saída: resultados/interseccional_2023_parte3.csv (a) e prints de (b)/(c).
"""
import warnings
warnings.filterwarnings("ignore")

import gc
import csv

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from pathlib import Path

from analise_bivariada_e_regressao_v2 import ler_microdados, preparar
from analise_interseccional_20260916 import rr_celulas, bootstrap_reri

BASE = Path(__file__).parent
OUT_A = BASE / "resultados" / "interseccional_2023_parte3.csv"

CAMPOS_A = ["par", "desfecho", "prev_00", "prev_10", "prev_01", "prev_11",
            "rr10", "rr01", "rr11", "reri", "razao_razoes", "p_c11",
            "reri_ic95_low", "reri_ic95_high", "n_boot_validas"]


def escrever_linha(linha, primeira, path, campos):
    modo = "w" if primeira else "a"
    with open(path, modo, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        if primeira:
            w.writeheader()
        w.writerow(linha)


def ajustar_glm(df, formula, desfecho):
    sub = df.dropna(subset=["peso", "upa"]).copy()
    w = sub["peso"] / sub["peso"].mean()
    model = smf.glm(formula, data=sub, family=sm.families.Poisson(), var_weights=w)
    for attempt in [
        lambda: model.fit(cov_type="cluster", cov_kwds={"groups": sub["upa"]}),
        lambda: model.fit(cov_type="HC1"),
        lambda: model.fit(),
    ]:
        try:
            return attempt(), sub
        except np.linalg.LinAlgError:
            continue
    raise RuntimeError("Ajuste falhou.")


def main():
    df = ler_microdados()
    resp = preparar(df)
    del df
    gc.collect()

    # ---------------- (a) raça × rural/urbano ----------------
    primeira = True
    for desfecho in ["ia_total", "ia_grave"]:
        rotulo = "Cor/raça (preta+parda) × Situação domiciliar (rural)"
        print(f"\n=== (a) {rotulo} — {desfecho} ===", flush=True)
        res, sub = rr_celulas(resp, "negra", "rural", desfecho)
        print(f"  Prevalência: ref (não negra, urbano)={res['prev_00']:.1f}% | "
              f"só negra={res['prev_10']:.1f}% | só rural={res['prev_01']:.1f}% | "
              f"ambos={res['prev_11']:.1f}%", flush=True)
        print(f"  RR negra={res['rr10']:.3f} | RR rural={res['rr01']:.3f} | "
              f"RR ambos={res['rr11']:.3f} | RERI ponto={res['reri']:+.3f}", flush=True)
        lo, hi, n_ok = bootstrap_reri(sub, desfecho, n_boot=300)
        print(f"  IC95% bootstrap do RERI: [{lo:+.3f}, {hi:+.3f}]  contém zero: {lo < 0 < hi}",
              flush=True)
        linha = {"par": rotulo, "desfecho": desfecho,
                 **{k: v for k, v in res.items() if not k.startswith("n_")},
                 "reri_ic95_low": lo, "reri_ic95_high": hi, "n_boot_validas": n_ok}
        escrever_linha(linha, primeira, OUT_A, CAMPOS_A)
        primeira = False
        del sub, res
        gc.collect()

    # ---------------- (b) modelo conjunto, as 4 interações com raça juntas ----------------
    formula = ("{d} ~ negra + mulher + sem_fund + renda_q1 + rural "
               "+ negra:mulher + negra:sem_fund + negra:renda_q1 + negra:rural")
    for desfecho in ["ia_total", "ia_grave"]:
        print(f"\n=== (b) Modelo conjunto, ajustado, — {desfecho} ===", flush=True)
        res, sub = ajustar_glm(resp, formula.format(d=desfecho), desfecho)
        print(f"  N={len(sub):,}", flush=True)
        for termo in ["negra", "mulher", "sem_fund", "renda_q1", "rural",
                      "negra:mulher", "negra:sem_fund", "negra:renda_q1", "negra:rural"]:
            b = res.params[termo]
            se = res.bse[termo]
            rr = np.exp(b)
            ic_lo = np.exp(b - 1.96 * se)
            ic_hi = np.exp(b + 1.96 * se)
            p = res.pvalues[termo]
            marca = "efeito principal" if ":" not in termo else "interação"
            print(f"    [{marca:16s}] {termo:18s} RR={rr:.3f} (IC95% {ic_lo:.3f}-{ic_hi:.3f}) "
                  f"p={p:.4f}", flush=True)
        del sub
        gc.collect()

    # ---------------- (c) gradiente de desvantagem acumulada ----------------
    resp["n_desvantagens"] = resp["mulher"] + resp["sem_fund"] + resp["renda_q1"] + resp["rural"]
    print("\n=== (c) Gradiente de desvantagem acumulada (mulher+sem_fund+renda_q1+rural, 0–4) ===",
          flush=True)
    print("Prevalência ponderada de IA total e IA grave, por número de desvantagens × raça:",
          flush=True)
    for desfecho in ["ia_total", "ia_grave"]:
        print(f"\n  -- {desfecho} --", flush=True)
        tab = resp.groupby(["negra", "n_desvantagens"]).apply(
            lambda d: pd.Series({
                "pct": np.average(d[desfecho], weights=d["peso"]) * 100,
                "n": len(d),
            })
        ).reset_index()
        for _, row in tab.iterrows():
            grupo = "negra" if row["negra"] == 1 else "não negra"
            print(f"    {grupo:10s} | {int(row['n_desvantagens'])} desvantagens: "
                  f"{row['pct']:.1f}% (n={int(row['n'])})", flush=True)

        formula_c = f"{desfecho} ~ negra + n_desvantagens + negra:n_desvantagens"
        res, sub = ajustar_glm(resp, formula_c, desfecho)
        b_slope_ref = res.params["n_desvantagens"]
        b_slope_int = res.params["negra:n_desvantagens"]
        b_slope_negra = b_slope_ref + b_slope_int
        p_int = res.pvalues["negra:n_desvantagens"]
        print(f"    Inclinação (log-RR por desvantagem adicional): não negra={b_slope_ref:.3f} "
              f"(RR por desvantagem={np.exp(b_slope_ref):.3f}) | "
              f"negra={b_slope_negra:.3f} (RR por desvantagem={np.exp(b_slope_negra):.3f})",
              flush=True)
        print(f"    Diferença de inclinação (negra × n_desvantagens): p={p_int:.4f}", flush=True)
        del sub
        gc.collect()

    print(f"\nSalvo (a): {OUT_A}", flush=True)


if __name__ == "__main__":
    main()
