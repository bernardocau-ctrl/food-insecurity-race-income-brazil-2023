# -*- coding: utf-8 -*-
"""
analise_consolidada_artigo3_20260925.py

Analise consolidada para o manuscrito em ingles do Artigo 3 (interseccionalidade
raca x sexo x instrucao x renda x situacao domiciliar na inseguranca alimentar,
PNADC T4 2023). Reusa ler_microdados/preparar de analise_bivariada_e_regressao_v2
-- mesma fonte de verdade das analises de 16/09/2026.

Por que existe: as rodadas de 16/09 imprimiram o modelo conjunto e o gradiente
sem salvar, e nunca salvaram o IC nem o p da interacao MULTIPLICATIVA (razao de
razoes). Este script gera tudo em CSV, com IC, para o manuscrito.

Saidas (pasta dados/v2_20260925 do artigo):
  t1_descritiva.csv        prevalencia ponderada (IC95% linearizado por UPA) por categoria
  t2_pares.csv             4 pares x 2 desfechos: RR das celulas, RoR (IC, p),
                           RERI (ponto + IC95% pelo metodo delta), RERI esperado
                           sob nulo multiplicativo
  t3_conjunto.csv         modelo conjunto (4 interacoes) + teste de Wald conjunto
  t4_gradiente_prev.csv   prevalencia por n. de desvantagens x raca (IC), diferenca de risco
  t5_gradiente_modelos.csv inclinacao relativa (Poisson) e absoluta (linear) por raca
  t6_estratificado.csv    razao de prevalencia de raca/sexo dentro de estratos de renda,
                           instrucao e raca (ajustada)
  t7_tripla.csv           interacao de 3a ordem (raca x sexo x renda; raca x sexo x instrucao)
"""
import warnings
warnings.filterwarnings("ignore")

import gc
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from analise_bivariada_e_regressao_v2 import ler_microdados, preparar

OUT = (Path(__file__).parent / "artigos" /
       "03_ARTIGO3_INTERSECCIONALIDADE_RACA_IA" / "dados" / "v2_20260925")
OUT.mkdir(parents=True, exist_ok=True)

DESFECHOS = ["ia_total", "ia_grave"]
Z = 1.959964


def fit_poisson(df, formula, cols):
    sub = df.dropna(subset=cols + ["peso", "upa"]).copy()
    sub = sub[sub["peso"] > 0]
    w = sub["peso"] / sub["peso"].mean()
    m = smf.glm(formula, data=sub, family=sm.families.Poisson(), var_weights=w)
    for attempt in (
        lambda: m.fit(cov_type="cluster", cov_kwds={"groups": sub["upa"]}),
        lambda: m.fit(cov_type="HC1"),
    ):
        try:
            return attempt(), sub
        except np.linalg.LinAlgError:
            continue
    raise RuntimeError("falhou: " + formula)


def fit_linear(df, formula, cols):
    sub = df.dropna(subset=cols + ["peso", "upa"]).copy()
    sub = sub[sub["peso"] > 0]
    w = sub["peso"] / sub["peso"].mean()
    m = smf.glm(formula, data=sub, family=sm.families.Gaussian(), var_weights=w)
    return m.fit(cov_type="cluster", cov_kwds={"groups": sub["upa"]}), sub


def prev_ci(sub, y):
    return prev_ci_full(sub, y)[:3]


def prev_ci_full(sub, y):
    """Prevalencia ponderada com IC95% (logit) por linearizacao de Taylor
    com conglomerado = UPA (sem estrato: aproximacao conservadora).
    Devolve (p%, lo%, hi%, ep_p em pontos percentuais)."""
    w = sub["peso"].to_numpy(float)
    yy = sub[y].to_numpy(float)
    p = np.sum(w * yy) / np.sum(w)
    z = w * (yy - p) / np.sum(w)
    tot = pd.Series(z).groupby(sub["upa"].to_numpy()).sum()
    n = len(tot)
    var = n / (n - 1) * np.sum((tot - tot.mean()) ** 2)
    se = np.sqrt(var)
    if 0 < p < 1:
        sl = se / (p * (1 - p))
        lo = 1 / (1 + np.exp(-(np.log(p / (1 - p)) - Z * sl)))
        hi = 1 / (1 + np.exp(-(np.log(p / (1 - p)) + Z * sl)))
    else:
        lo = hi = p
    return p * 100, lo * 100, hi * 100, se * 100


def main():
    df = ler_microdados()
    r = preparar(df)
    del df
    gc.collect()

    r["renda_cat"] = np.select(
        [r.renda_q1 == 1, r.renda_q2 == 1, r.renda_q3 == 1, r.renda_q4 == 1],
        ["q1", "q2", "q3", "q4"], default="q5")
    r["instr_cat"] = np.select(
        [r.sem_fund == 1, r.fund_med == 1, r.medio_comp == 1],
        ["sem_fund", "fund_med", "medio_comp"], default="superior")
    print("N analitico:", len(r), flush=True)

    # ------------------------------------------------------------ T1
    linhas = []
    def add_row(rot, cat, sub):
        n = len(sub)
        row = {"variavel": rot, "categoria": cat, "n": n,
               "pct_pond_amostra": sub["peso"].sum() / r["peso"].sum() * 100}
        for d in DESFECHOS:
            p, lo, hi = prev_ci(sub, d)
            row[f"{d}_pct"], row[f"{d}_lo"], row[f"{d}_hi"] = p, lo, hi
        linhas.append(row)
    add_row("Total", "Brasil", r)
    for rot, col, cats in [
        ("Cor/raca", "negra", {0: "nao negra", 1: "negra (preta+parda)"}),
        ("Sexo", "mulher", {0: "homem", 1: "mulher"}),
        ("Situacao", "rural", {0: "urbano", 1: "rural"}),
    ]:
        for k, nome in cats.items():
            add_row(rot, nome, r[r[col] == k])
    for c in ["sem_fund", "fund_med", "medio_comp", "superior"]:
        add_row("Instrucao", c, r[r.instr_cat == c])
    for c in ["q1", "q2", "q3", "q4", "q5"]:
        add_row("Renda pc", c, r[r.renda_cat == c])
    pd.DataFrame(linhas).to_csv(OUT / "t1_descritiva.csv", index=False)
    print("T1 ok", flush=True)

    # ------------------------------------------------------------ T2
    pares = [("negra", "mulher", "Race x Sex (woman)"),
             ("negra", "sem_fund", "Race x Education (<= incomplete primary)"),
             ("negra", "renda_q1", "Race x Income (<= 1/4 MW per capita)"),
             ("negra", "rural", "Race x Residence (rural)")]
    linhas = []
    for a, b, rot in pares:
        for d in DESFECHOS:
            sub = r.dropna(subset=[a, b, d, "peso", "upa"]).copy()
            sub["c10"] = ((sub[a] == 1) & (sub[b] == 0)).astype(int)
            sub["c01"] = ((sub[a] == 0) & (sub[b] == 1)).astype(int)
            sub["c11"] = ((sub[a] == 1) & (sub[b] == 1)).astype(int)
            res, _ = fit_poisson(sub, f"{d} ~ c10 + c01 + c11", [a, b, d])
            bb = res.params
            V = res.cov_params()
            rr = {k: float(np.exp(bb[k])) for k in ["c10", "c01", "c11"]}
            ci = {k: (float(np.exp(bb[k] - Z * res.bse[k])), float(np.exp(bb[k] + Z * res.bse[k])))
                  for k in ["c10", "c01", "c11"]}
            reri = rr["c11"] - rr["c10"] - rr["c01"] + 1
            g = np.array([-rr["c10"], -rr["c01"], rr["c11"]])
            Vs = V.loc[["c10", "c01", "c11"], ["c10", "c01", "c11"]].to_numpy()
            se_reri = float(np.sqrt(g @ Vs @ g))
            # RoR via modelo com termo de interacao
            res2, _ = fit_poisson(sub, f"{d} ~ {a} + {b} + {a}:{b}", [a, b, d])
            t = f"{a}:{b}"
            ror = float(np.exp(res2.params[t]))
            ror_ci = (float(np.exp(res2.params[t] - Z * res2.bse[t])),
                      float(np.exp(res2.params[t] + Z * res2.bse[t])))
            prevs = {}
            for nome, m in [("p00", (sub[a] == 0) & (sub[b] == 0)), ("p10", (sub[a] == 1) & (sub[b] == 0)),
                            ("p01", (sub[a] == 0) & (sub[b] == 1)), ("p11", (sub[a] == 1) & (sub[b] == 1))]:
                s = sub[m]
                prevs[nome] = prev_ci(s, d)[0]
                prevs["n" + nome[1:]] = len(s)
            linhas.append({
                "par": rot, "desfecho": d, **prevs,
                "rr10": rr["c10"], "rr10_lo": ci["c10"][0], "rr10_hi": ci["c10"][1],
                "rr01": rr["c01"], "rr01_lo": ci["c01"][0], "rr01_hi": ci["c01"][1],
                "rr11": rr["c11"], "rr11_lo": ci["c11"][0], "rr11_hi": ci["c11"][1],
                "reri": reri, "reri_lo_delta": reri - Z * se_reri, "reri_hi_delta": reri + Z * se_reri,
                "reri_esperado_nulo_mult": (rr["c10"] - 1) * (rr["c01"] - 1),
                "ror": ror, "ror_lo": ror_ci[0], "ror_hi": ror_ci[1],
                "ror_p": float(res2.pvalues[t]),
            })
            print("T2", rot, d, f"RERI={reri:.3f} RoR={ror:.3f}", flush=True)
            del sub
            gc.collect()
    pd.DataFrame(linhas).to_csv(OUT / "t2_pares.csv", index=False)

    # ------------------------------------------------------------ T3
    termos = ["negra", "mulher", "sem_fund", "renda_q1", "rural",
              "negra:mulher", "negra:sem_fund", "negra:renda_q1", "negra:rural"]
    f = ("{d} ~ negra + mulher + sem_fund + renda_q1 + rural + negra:mulher "
         "+ negra:sem_fund + negra:renda_q1 + negra:rural")
    linhas = []
    for d in DESFECHOS:
        res, sub = fit_poisson(r, f.format(d=d), [d])
        for t in termos:
            linhas.append({"desfecho": d, "termo": t,
                           "tipo": "interacao" if ":" in t else "principal",
                           "rr": np.exp(res.params[t]),
                           "lo": np.exp(res.params[t] - Z * res.bse[t]),
                           "hi": np.exp(res.params[t] + Z * res.bse[t]),
                           "p": res.pvalues[t]})
        R = np.zeros((4, len(res.params)))
        names = list(res.params.index)
        for i, t in enumerate(["negra:mulher", "negra:sem_fund", "negra:renda_q1", "negra:rural"]):
            R[i, names.index(t)] = 1
        w = res.wald_test(R, scalar=True)
        linhas.append({"desfecho": d, "termo": "WALD_conjunto_4gl", "tipo": "teste",
                       "rr": float(w.statistic), "lo": np.nan, "hi": np.nan, "p": float(w.pvalue)})
        print("T3", d, "N=", len(sub), flush=True)
    pd.DataFrame(linhas).to_csv(OUT / "t3_conjunto.csv", index=False)

    # ------------------------------------------------------------ T4/T5
    r["n_desv"] = r["mulher"] + r["sem_fund"] + r["renda_q1"] + r["rural"]
    linhas = []
    for d in DESFECHOS:
        for k in range(5):
            row = {"desfecho": d, "n_desv": k}
            for g, nome in [(0, "nao_negra"), (1, "negra")]:
                s = r[(r.negra == g) & (r.n_desv == k)]
                p, lo, hi = prev_ci(s, d) if len(s) > 1 else (np.nan,) * 3
                row.update({f"{nome}_n": len(s), f"{nome}_pct": p, f"{nome}_lo": lo, f"{nome}_hi": hi})
            row["diferenca_pp"] = row["negra_pct"] - row["nao_negra_pct"]
            row["razao"] = row["negra_pct"] / row["nao_negra_pct"] if row["nao_negra_pct"] else np.nan
            linhas.append(row)
    pd.DataFrame(linhas).to_csv(OUT / "t4_gradiente_prev.csv", index=False)

    linhas = []
    for d in DESFECHOS:
        res, _ = fit_poisson(r, f"{d} ~ negra + n_desv + negra:n_desv", [d])
        b0, bi = res.params["n_desv"], res.params["negra:n_desv"]
        V = res.cov_params()
        se_neg = float(np.sqrt(V.loc["n_desv", "n_desv"] + V.loc["negra:n_desv", "negra:n_desv"]
                               + 2 * V.loc["n_desv", "negra:n_desv"]))
        linhas.append({"desfecho": d, "escala": "relativa (RR por desvantagem)",
                       "nao_negra": np.exp(b0), "nao_negra_lo": np.exp(b0 - Z * res.bse["n_desv"]),
                       "nao_negra_hi": np.exp(b0 + Z * res.bse["n_desv"]),
                       "negra": np.exp(b0 + bi), "negra_lo": np.exp(b0 + bi - Z * se_neg),
                       "negra_hi": np.exp(b0 + bi + Z * se_neg),
                       "p_diferenca": res.pvalues["negra:n_desv"]})
        res, _ = fit_linear(r, f"{d} ~ negra + n_desv + negra:n_desv", [d])
        b0, bi = res.params["n_desv"] * 100, res.params["negra:n_desv"] * 100
        V = res.cov_params()
        se_neg = 100 * float(np.sqrt(V.loc["n_desv", "n_desv"] + V.loc["negra:n_desv", "negra:n_desv"]
                                     + 2 * V.loc["n_desv", "negra:n_desv"]))
        linhas.append({"desfecho": d, "escala": "absoluta (pp por desvantagem)",
                       "nao_negra": b0, "nao_negra_lo": b0 - Z * 100 * res.bse["n_desv"],
                       "nao_negra_hi": b0 + Z * 100 * res.bse["n_desv"],
                       "negra": b0 + bi, "negra_lo": b0 + bi - Z * se_neg,
                       "negra_hi": b0 + bi + Z * se_neg,
                       "p_diferenca": res.pvalues["negra:n_desv"]})
        print("T5", d, flush=True)
    pd.DataFrame(linhas).to_csv(OUT / "t5_gradiente_modelos.csv", index=False)

    # ------------------------------------------------------------ T6
    linhas = []
    def estrato(rotulo_estrat, cat, sub, expos, cov):
        for d in DESFECHOS:
            res, s2 = fit_poisson(sub, f"{d} ~ {expos}{cov}", [d])
            p1, p1lo, p1hi, se1 = prev_ci_full(s2[s2[expos] == 1], d)
            p0, p0lo, p0hi, se0 = prev_ci_full(s2[s2[expos] == 0], d)
            se_dif = float(np.sqrt(se1 ** 2 + se0 ** 2))
            linhas.append({"exposicao": expos, "estratificado_por": rotulo_estrat, "estrato": cat,
                           "desfecho": d, "n": len(s2), "prev_exposto": p1, "prev_exposto_lo": p1lo,
                           "prev_exposto_hi": p1hi, "prev_nao_exposto": p0,
                           "prev_nao_exposto_lo": p0lo, "prev_nao_exposto_hi": p0hi,
                           "dif_pp": p1 - p0, "dif_pp_lo": p1 - p0 - Z * se_dif,
                           "dif_pp_hi": p1 - p0 + Z * se_dif, "rr_ajustado": np.exp(res.params[expos]),
                           "lo": np.exp(res.params[expos] - Z * res.bse[expos]),
                           "hi": np.exp(res.params[expos] + Z * res.bse[expos]),
                           "p": res.pvalues[expos]})
    for c in ["q1", "q2", "q3", "q4", "q5"]:
        s = r[r.renda_cat == c]
        estrato("renda", c, s, "negra", " + mulher + C(instr_cat) + rural")
        estrato("renda", c, s, "mulher", " + negra + C(instr_cat) + rural")
    for c in ["sem_fund", "fund_med", "medio_comp", "superior"]:
        s = r[r.instr_cat == c]
        estrato("instrucao", c, s, "negra", " + mulher + C(renda_cat) + rural")
    for g, nome in [(0, "nao_negra"), (1, "negra")]:
        s = r[r.negra == g]
        estrato("raca", nome, s, "mulher", " + C(instr_cat) + C(renda_cat) + rural")
    pd.DataFrame(linhas).to_csv(OUT / "t6_estratificado.csv", index=False)
    print("T6 ok", flush=True)

    # ------------------------------------------------------------ T7
    linhas = []
    for mod in ["renda_q1", "sem_fund"]:
        for d in DESFECHOS:
            res, _ = fit_poisson(r, f"{d} ~ negra * mulher * {mod}", [d])
            t = f"negra:mulher:{mod}"
            linhas.append({"terceira_dimensao": mod, "desfecho": d, "termo": t,
                           "rr": np.exp(res.params[t]),
                           "lo": np.exp(res.params[t] - Z * res.bse[t]),
                           "hi": np.exp(res.params[t] + Z * res.bse[t]), "p": res.pvalues[t]})
            print("T7", mod, d, flush=True)
    pd.DataFrame(linhas).to_csv(OUT / "t7_tripla.csv", index=False)
    print("FIM. Saidas em", OUT, flush=True)


if __name__ == "__main__":
    main()
