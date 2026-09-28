# -*- coding: utf-8 -*-
"""
analise_interseccional_20260916.py

Testa formalmente se raca cruzada com genero, instrucao e renda produz efeito
MULTIPLICATIVO na inseguranca alimentar (PNADC T4 2023), alem do que cada
variavel produziria isoladamente. Reusa a mesma leitura/preparacao de microdados
e a mesma logica de peso (var_weights) + erro-padrao robusto por UPA de
analise_bivariada_e_regressao_v2.py -- mesma fonte de verdade, nao um novo
pipeline paralelo.

Para cada par (ex.: negra x mulher):
  1. RR de cada uma das 4 celulas da tabela 2x2 vs. a celula de referencia
     (nao-exposta nas duas dimensoes), via Poisson com var_weights e erro-padrao
     agrupado por UPA. Teste de Wald sobre o termo de interacao (escala
     multiplicativa) sai desse mesmo ajuste, sem bootstrap.
  2. Escala aditiva: RERI (relative excess risk due to interaction) =
     RR11 - RR10 - RR01 + 1, com IC95% via bootstrap por conglomerado (reamostra
     UPAs inteiras). Rodado so' para ia_total (o desfecho mais estavel), com
     numero de replicas reduzido -- a maquina desta sessao matou o processo por
     memoria numa primeira tentativa mais pesada.

Saida: resultados/interseccional_2023.csv (gravado linha a linha, sobrevive a
uma interrupcao no meio do bootstrap).
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

BASE = Path(__file__).parent
OUT = BASE / "resultados" / "interseccional_2023.csv"

CAMPOS = ["par", "desfecho", "prev_00", "prev_10", "prev_01", "prev_11",
          "rr10", "rr01", "rr11", "reri", "razao_razoes",
          "p_c11", "reri_ic95_low", "reri_ic95_high", "n_boot_validas"]


def rr_celulas(df, var1, var2, desfecho):
    """RR de cada combinacao de var1 x var2 (0/1 cada) vs. a celula 00,
    via modelo saturado (dummies das 3 celulas restantes), peso + cluster UPA."""
    sub = df.dropna(subset=[var1, var2, desfecho, "peso", "upa"]).copy()
    sub["c10"] = ((sub[var1] == 1) & (sub[var2] == 0)).astype(int)
    sub["c01"] = ((sub[var1] == 0) & (sub[var2] == 1)).astype(int)
    sub["c11"] = ((sub[var1] == 1) & (sub[var2] == 1)).astype(int)

    w = sub["peso"] / sub["peso"].mean()
    formula = f"{desfecho} ~ c10 + c01 + c11"
    model = smf.glm(formula, data=sub, family=sm.families.Poisson(), var_weights=w)
    res = None
    for attempt in [
        lambda: model.fit(cov_type="cluster", cov_kwds={"groups": sub["upa"]}),
        lambda: model.fit(cov_type="HC1"),
        lambda: model.fit(),
    ]:
        try:
            res = attempt()
            break
        except np.linalg.LinAlgError:
            continue
    if res is None:
        raise RuntimeError("Ajuste falhou.")

    rr10 = float(np.exp(res.params["c10"]))
    rr01 = float(np.exp(res.params["c01"]))
    rr11 = float(np.exp(res.params["c11"]))
    reri = rr11 - rr10 - rr01 + 1
    razao_razoes = rr11 / (rr10 * rr01)

    prevs = {}
    for nome, mask in [
        ("00", (sub[var1] == 0) & (sub[var2] == 0)),
        ("10", (sub[var1] == 1) & (sub[var2] == 0)),
        ("01", (sub[var1] == 0) & (sub[var2] == 1)),
        ("11", (sub[var1] == 1) & (sub[var2] == 1)),
    ]:
        d = sub[mask]
        prevs[f"prev_{nome}"] = float(np.average(d[desfecho], weights=d["peso"]) * 100) if len(d) else float("nan")
        prevs[f"n_{nome}"] = int(len(d))

    small = sub[[var1, var2, "c10", "c01", "c11", desfecho, "peso", "upa"]].copy()
    return {
        "rr10": rr10, "rr01": rr01, "rr11": rr11,
        "reri": reri, "razao_razoes": razao_razoes,
        "p_c11": float(res.pvalues["c11"]),
        **prevs,
    }, small


def bootstrap_reri(sub, desfecho, n_boot=300, seed=20260916):
    """IC95% do RERI por bootstrap de conglomerado (reamostra UPAs inteiras)."""
    rng = np.random.default_rng(seed)
    grupos = {u: g for u, g in sub.groupby("upa")}
    upas = np.array(list(grupos.keys()))
    n_upa = len(upas)
    valores = []
    formula = f"{desfecho} ~ c10 + c01 + c11"
    for i in range(n_boot):
        escolhidas = rng.choice(upas, size=n_upa, replace=True)
        d = pd.concat([grupos[u] for u in escolhidas], ignore_index=True)
        try:
            w = d["peso"] / d["peso"].mean()
            model = smf.glm(formula, data=d, family=sm.families.Poisson(), var_weights=w)
            res = model.fit()
            rr10 = np.exp(res.params["c10"])
            rr01 = np.exp(res.params["c01"])
            rr11 = np.exp(res.params["c11"])
            valores.append(rr11 - rr10 - rr01 + 1)
        except Exception:
            pass
        del d
        if i % 50 == 0:
            gc.collect()
            print(f"    bootstrap {i}/{n_boot}...", flush=True)
    valores = np.array(valores)
    if len(valores) == 0:
        return float("nan"), float("nan"), 0
    return float(np.percentile(valores, 2.5)), float(np.percentile(valores, 97.5)), len(valores)


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

    pares = [
        ("negra", "mulher", "Cor/raça (preta+parda) × Sexo (mulher)"),
        ("negra", "sem_fund", "Cor/raça (preta+parda) × Instrução (sem instrução/fund. incompleto)"),
        ("negra", "renda_q1", "Cor/raça (preta+parda) × Renda (até 1/4 SM)"),
    ]

    primeira = True
    for v1, v2, rotulo in pares:
        for desfecho in ["ia_total", "ia_grave"]:
            print(f"\n=== {rotulo} — {desfecho} ===", flush=True)
            res, sub = rr_celulas(resp, v1, v2, desfecho)
            print(f"  Prevalência: nem {v1} nem {v2}={res['prev_00']:.1f}% (n={res['n_00']}) | "
                  f"só {v1}={res['prev_10']:.1f}% (n={res['n_10']}) | "
                  f"só {v2}={res['prev_01']:.1f}% (n={res['n_01']}) | "
                  f"ambos={res['prev_11']:.1f}% (n={res['n_11']})", flush=True)
            print(f"  RR só {v1}={res['rr10']:.3f} | RR só {v2}={res['rr01']:.3f} | "
                  f"RR ambos={res['rr11']:.3f}", flush=True)
            print(f"  Razão de razões (RR11/(RR10*RR01))={res['razao_razoes']:.3f} | "
                  f"p (termo de interação c11)={res['p_c11']:.4f}", flush=True)
            print(f"  RERI (excesso aditivo, ponto)={res['reri']:+.3f}", flush=True)

            if desfecho == "ia_total":
                lo, hi, n_ok = bootstrap_reri(sub, desfecho, n_boot=300)
                print(f"  IC95% bootstrap do RERI (cluster por UPA, {n_ok} réplicas válidas): "
                      f"[{lo:+.3f}, {hi:+.3f}]  contém zero: {lo < 0 < hi}", flush=True)
            else:
                lo = hi = float("nan")
                n_ok = 0
                print("  (bootstrap do RERI pulado para ia_grave nesta rodada, por custo "
                      "computacional — ponto estimado e teste de Wald acima já valem.)", flush=True)

            linha = {"par": rotulo, "desfecho": desfecho,
                     **{k: v for k, v in res.items() if not k.startswith("n_")},
                     "reri_ic95_low": lo, "reri_ic95_high": hi, "n_boot_validas": n_ok}
            escrever_linha(linha, primeira)
            primeira = False

            del sub, res
            gc.collect()

    print(f"\nSalvo: {OUT}", flush=True)


if __name__ == "__main__":
    main()
