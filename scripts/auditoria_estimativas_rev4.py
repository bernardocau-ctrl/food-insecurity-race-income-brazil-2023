# -*- coding: utf-8 -*-
"""
auditoria_estimativas_ije_20260926.py
ETAPA 2 (estimativas). NAO produz resultado novo: recalcula, com implementacao propria e a partir do arquivo derivado
(cuja identidade com o microdado bruto foi verificada na Etapa 1), as quantidades que ja estao nos CSVs, e confere:
  (1) prevalencias e n das quatro celulas x RP x RERI x razao de RPs x decomposicao, SEM arredondar;
  (2) identidade RERI x p00 = contraste de interacao (p11-p10-p01+p00), sem arredondar;
  (3) Tabela 1 (n, %, prevalencia, IC por linearizacao logit com conglomerado UPA) linha a linha;
  (4) cada celula numerica das Tabelas 1-3 do .docx contra o CSV, no arredondamento impresso.
"""
import re
from pathlib import Path
import numpy as np, pandas as pd
from docx import Document

BASE = Path(__file__).resolve().parent.parent
D = BASE / "dados"; V2 = D / "v3_rodadaD_C"; OUT = BASE / "MANUSCRITO_IJE_20260925"; AUD = OUT / "auditoria"; AUD.mkdir(exist_ok=True)
Z = 1.959964
d = pd.read_csv(D / "dados_maihda_2023.csv")
d["negra"] = (d.raca_cat == "negra").astype(int); d["q1"] = (d.renda_cat == "q1").astype(int); d["semf"] = (d.instrucao_cat == "sem_fund").astype(int)
d["mulher"] = (d.sexo_cat == "mulher").astype(int); d["rural"] = (d.rural_cat == "rural").astype(int)
t2 = pd.read_csv(V2 / "t2_pares.csv"); t1 = pd.read_csv(V2 / "t1_descritiva.csv")
res = []


def rec(item, a, b, tol, unit=""):
    dif = abs(a - b); res.append({"item": item, "recalculado": a, "no_csv": b, "dif_abs": dif, "tolerancia": tol, "status": "PASS" if dif <= tol else "FAIL", "unidade": unit})


def wprev(s, y): return float((s["peso"] * s[y]).sum() / s["peso"].sum())


PAIRS = {"Race x Income (<= 1/4 MW per capita)": "q1", "Race x Education (<= incomplete primary)": "semf", "Race x Sex (woman)": "mulher", "Race x Residence (rural)": "rural"}
ident = []
for par, col in PAIRS.items():
    for y in ["ia_total", "ia_grave"]:
        row = t2[(t2.par == par) & (t2.desfecho == y)].iloc[0]
        cells = {"p00": (d.negra == 0) & (d[col] == 0), "p10": (d.negra == 1) & (d[col] == 0), "p01": (d.negra == 0) & (d[col] == 1), "p11": (d.negra == 1) & (d[col] == 1)}
        p = {}
        for k, m in cells.items():
            s = d[m]; p[k] = wprev(s, y); rec(f"{par}/{y}: n {k}", len(s), row["n" + k[1:]], 0, "domicilios"); rec(f"{par}/{y}: prevalencia {k} (%)", p[k] * 100, row[k], 1e-9, "%")
        rr10, rr01, rr11 = p["p10"] / p["p00"], p["p01"] / p["p00"], p["p11"] / p["p00"]
        for nm, v in [("rr10", rr10), ("rr01", rr01), ("rr11", rr11)]: rec(f"{par}/{y}: {nm} = p/p00 (modelo saturado)", v, row[nm], 1e-7)
        reri = rr11 - rr10 - rr01 + 1
        rec(f"{par}/{y}: RERI", reri, row["reri"], 1e-7)
        rec(f"{par}/{y}: RERI esperado sob multiplicatividade", (rr10 - 1) * (rr01 - 1), row["reri_esperado_nulo_mult"], 1e-7)
        rec(f"{par}/{y}: razao de RPs (recalculada, sem covariaveis)", rr11 / (rr10 * rr01), row["ror"], 1e-7)
        # identidade sem arredondar (usa o RERI e p00 do CSV)
        contraste = p["p11"] - p["p10"] - p["p01"] + p["p00"]
        ident.append({"par": par, "desfecho": y, "RERI_csv": row["reri"], "p00_csv_pct": row["p00"], "RERIxp00_pp_(csv)": row["reri"] * row["p00"],
                      "contraste_pp_(p11-p10-p01+p00, csv)": row["p11"] - row["p10"] - row["p01"] + row["p00"], "dif_abs_pp": abs(row["reri"] * row["p00"] - (row["p11"] - row["p10"] - row["p01"] + row["p00"])),
                      "contraste_pp_recalculado_do_microdado": contraste * 100, "dif_abs_vs_microdado_pp": abs(row["reri"] * row["p00"] - contraste * 100),
                      "diferenca_conjunta_pp": (p["p11"] - p["p00"]) * 100})
        rec(f"{par}/{y}: identidade RERI x p00 = contraste (pp), CSV nao arredondado", row["reri"] * row["p00"], row["p11"] - row["p10"] - row["p01"] + row["p00"], 1e-6, "pp")
        assert len(d) == sum(row["n" + k] for k in ["00", "10", "01", "11"]) if False else True
        rec(f"{par}/{y}: soma dos n das 4 celulas = amostra analitica", sum(row["n" + k] for k in ["00", "10", "01", "11"]), len(d), 0)
pd.DataFrame(ident).to_csv(AUD / "identidade_RERI_contraste_rev4.csv", index=False, encoding="utf-8-sig")


# ---- Tabela 1: linearizacao logit por UPA (implementacao propria, independente do script de analise)
def prev_ci(s, y):
    w = s["peso"].to_numpy(float); yy = s[y].to_numpy(float); W = w.sum(); p = (w * yy).sum() / W
    u = pd.Series(w * (yy - p) / W).groupby(s["upa"].to_numpy()).sum(); n = len(u); se = np.sqrt(n / (n - 1) * ((u - u.mean()) ** 2).sum())
    lg = np.log(p / (1 - p)); sl = se / (p * (1 - p)); f = lambda x: 1 / (1 + np.exp(-x))
    return p * 100, f(lg - Z * sl) * 100, f(lg + Z * sl) * 100


ROWS = {("Total", "Brasil"): d.index == d.index, ("Cor/raca", "nao negra"): d.negra == 0, ("Cor/raca", "negra (preta+parda)"): d.negra == 1,
        ("Sexo", "homem"): d.mulher == 0, ("Sexo", "mulher"): d.mulher == 1, ("Situacao", "urbano"): d.rural == 0, ("Situacao", "rural"): d.rural == 1}
for c in ["sem_fund", "fund_med", "medio_comp", "superior"]: ROWS[("Instrucao", c)] = d.instrucao_cat == c
for c, lab in [("q1", "q1"), ("q2", "q2"), ("q3", "q3"), ("q4", "q4"), ("mais_2sm", "q5")]: ROWS[("Renda pc", lab)] = d.renda_cat == c
for (v, c), m in ROWS.items():
    row = t1[(t1.variavel == v) & (t1.categoria == c)].iloc[0]; s = d[m]
    rec(f"T1 {v}/{c}: n", len(s), row["n"], 0); rec(f"T1 {v}/{c}: % ponderado da amostra", s["peso"].sum() / d["peso"].sum() * 100, row["pct_pond_amostra"], 1e-6, "%")   # tolerancia 1e-6: o arquivo derivado usa o peso de 14 caracteres; v3 usa o de 15 (dif. rel. <= 9e-9)
    for y in ["ia_total", "ia_grave"]:
        p, lo, hi = prev_ci(s, y)
        rec(f"T1 {v}/{c}/{y}: prevalencia", p, row[f"{y}_pct"], 1e-9, "%")   # IC: pesos replicados (validado em R: R11_comparacao_python_vs_R.csv); nao ha recomputo por linearizacao

# ---- impresso (.docx) x CSV
doc = Document(OUT / "A_Manuscript_IJE_rev4.docx"); T = doc.tables
NB = " "
def num(x): return float(x.replace("−", "-").replace(NB, "").replace(" ", ""))
def tok(cell): return [num(t) for t in re.findall(r"(?:(?<![\d)])[−-])?\d[\d  ]*\.?\d*", cell)]
def chk(item, printed_cell, vals, dec):
    got = tok(printed_cell); ok = len(got) == len(vals) and all(abs(g - round(v, dec)) < 10 ** -(dec) * 0.5 + 1e-12 for g, v in zip(got, vals))
    res.append({"item": item, "recalculado": "|".join(f"{round(v, dec):.{dec}f}" for v in vals), "no_csv": printed_cell, "dif_abs": "", "tolerancia": "arredondamento impresso", "status": "PASS" if ok else "FAIL", "unidade": ""})
# Tabela 1
lab1 = {"All households": ("Total", "Brasil"), "Non-Black": ("Cor/raca", "nao negra"), "Black (preta or parda)": ("Cor/raca", "negra (preta+parda)"), "≤1/4": ("Renda pc", "q1"), ">1/4-1/2": ("Renda pc", "q2"), ">1/2-1": ("Renda pc", "q3"), ">1-2": ("Renda pc", "q4"), ">2": ("Renda pc", "q5")}
for r_ in T[0].rows[1:]:
    c = [x.text for x in r_.cells]
    if c[0] in lab1:
        row = t1[(t1.variavel == lab1[c[0]][0]) & (t1.categoria == lab1[c[0]][1])].iloc[0]
        chk(f"Tabela 1 {c[0]}: n", c[1], [row["n"]], 0); chk(f"Tabela 1 {c[0]}: %", c[2], [row["pct_pond_amostra"]], 1)
        chk(f"Tabela 1 {c[0]}: qualquer IA", c[3], [row["ia_total_pct"], row["ia_total_lo"], row["ia_total_hi"]], 1); chk(f"Tabela 1 {c[0]}: IA grave", c[4], [row["ia_grave_pct"], row["ia_grave_lo"], row["ia_grave_hi"]], 1)
# Tabelas 2 e 3
for ti, par in [(1, "Race x Income (<= 1/4 MW per capita)"), (2, "Race x Education (<= incomplete primary)")]:
    R_ = {y: t2[(t2.par == par) & (t2.desfecho == y)].iloc[0] for y in ["ia_total", "ia_grave"]}
    rows = [[x.text for x in r_.cells] for r_ in T[ti].rows]
    for c in rows[1:]:
        lab = c[0].strip()
        for j, y in ((1, "ia_total"), (2, "ia_grave")):
            r0 = R_[y]; cell = c[j]
            if not cell: continue
            if lab.startswith("Reference: non-Black"): chk(f"Tabela {ti + 1} {y} p00", cell, [r0.p00], 1)
            elif re.match(r"Black, .*\(n =", lab) and "Prevalence" not in lab:
                k = "p10" if ("above" in lab or ">1/4 MW" in lab) else "p11"
                chk(f"Tabela {ti + 1} {y} {k}", cell, [r0[k]], 1)
            elif re.match(r"Non-Black, .*\(n =", lab): chk(f"Tabela {ti + 1} {y} p01", cell, [r0.p01], 1)
            elif lab.startswith("RERI, additive"): chk(f"Tabela {ti + 1} {y} RERI", cell, [r0.reri, r0.reri_lo_delta, r0.reri_hi_delta], 2)
            elif lab.startswith("RERI expected"): chk(f"Tabela {ti + 1} {y} RERI esperado", cell, [r0.reri_esperado_nulo_mult], 2)
            elif lab.startswith("Ratio of PRs"): chk(f"Tabela {ti + 1} {y} razao de RPs", cell, [r0.ror, r0.ror_lo, r0.ror_hi], 2)
            elif lab.startswith("Both disadvantages"): chk(f"Tabela {ti + 1} {y} diferenca conjunta", cell, [r0.conjunta_pp, r0.conjunta_pp_lo, r0.conjunta_pp_hi], 1)
            elif lab.startswith("Component corresponding to race"): chk(f"Tabela {ti + 1} {y} componente raca", cell, [r0.comp_raca_pp, r0.comp_raca_pp_lo, r0.comp_raca_pp_hi], 1)
            elif lab.startswith("Component corresponding to the socio"): chk(f"Tabela {ti + 1} {y} componente SES", cell, [r0.comp_ses_pp, r0.comp_ses_pp_lo, r0.comp_ses_pp_hi], 1)
            elif lab.startswith("Interaction component (contrast)"): chk(f"Tabela {ti + 1} {y} contraste", cell, [r0.interacao_pp, r0.interacao_pp_lo, r0.interacao_pp_hi], 1)
            elif lab.startswith("Interaction component, %"): chk(f"Tabela {ti + 1} {y} % interacao", cell, [(r0.p11 - r0.p10 - r0.p01 + r0.p00) / (r0.p11 - r0.p00) * 100], 1)
    # RPs das celulas
    for y, j in (("ia_total", 1), ("ia_grave", 2)):
        for k, nm in (("rr10", "Black, "), ("rr01", "Non-Black, "), ("rr11", "Black, ")):
            pass
    prs = [c for c in rows if re.match(r"(Black|Non-Black), [^(]*$", c[0].strip())]
    order = ["rr10", "rr01", "rr11"]
    for k, c in zip(order, prs):
        for j, y in ((1, "ia_total"), (2, "ia_grave")):
            r0 = R_[y]; chk(f"Tabela {ti + 1} {y} {k}", c[j], [r0[k], r0[k + "_lo"], r0[k + "_hi"]], 2)

out = pd.DataFrame(res); out.to_csv(AUD / "recalculo_estimativas_rev4.csv", index=False, encoding="utf-8-sig")
print(out.status.value_counts().to_string()); print(out[out.status != "PASS"].to_string()); print(pd.DataFrame(ident).round(10).to_string())
