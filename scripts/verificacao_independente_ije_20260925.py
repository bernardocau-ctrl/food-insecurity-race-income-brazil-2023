# -*- coding: utf-8 -*-
"""
verificacao_independente_ije_20260925.py

CONFRONTO INDEPENDENTE dos numeros do resumo/texto do manuscrito IJE. Nao produz estimativas novas para o
manuscrito: recalcula, com implementacao diferente da usada na analise (numpy puro, sem statsmodels), as
estimativas ja publicadas nos CSVs, e compara.

Implementacao independente:
  - prevalencias ponderadas por celula, PR = razao de prevalencias, RERI, razao de RPs, RERI esperado, decomposicao
  - IC do RERI e da razao de RPs por linearizacao (metodo delta) a partir de totais por UPA (sem GLM)
  - RP ajustada por IRLS Poisson escrito a mao (pesos + variancia robusta por conglomerado)
  - AUC por sklearn (se disponivel) e PCV/VPC por aritmetica a partir das variancias
Saida: MANUSCRITO_IJE_20260925/F_independent_verification.csv
"""
import sys, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
SAN = BASE.parent.parent
sys.path.insert(0, str(SAN))
from analise_bivariada_e_regressao_v2 import ler_microdados, preparar   # carga dos microdados (mesma fonte)

D = BASE / "dados" / "v2_20260925"; OUT = BASE / "MANUSCRITO_IJE_20260925"
t1 = pd.read_csv(D / "t1_descritiva.csv"); t2 = pd.read_csv(D / "t2_pares.csv"); t6 = pd.read_csv(D / "t6_estratificado.csv")
aten = pd.read_csv(BASE / "dados" / "atenuacao_renda_raca_sexo_2023.csv"); m1 = pd.read_csv(D / "m1_maihda_geral.csv").set_index("desfecho")
rows = []
Z = 1.959964


def add(item, indep, reported, tol, unit=""):
    d = abs(indep - reported)
    rows.append({"item": item, "independent": indep, "reported_in_csv": reported, "abs_diff": d, "tolerance": tol, "status": "PASS" if d <= tol else "DIFF", "unit": unit})


df = preparar(ler_microdados())
df = df[df["peso"] > 0].copy()
w = df["peso"].to_numpy(float); upa = df["upa"].to_numpy(); n = len(df)
add("analytic sample size (households)", n, float(t1[t1.variavel == "Total"].n.iloc[0]), 0, "n")
codes, G = pd.factorize(upa); G = len(G)


def cell_stats(mask_list, y):
    """medias ponderadas por celula, e covariancia por linearizacao com totais por UPA"""
    p = []; scores = []
    for m in mask_list:
        Wk = w[m].sum(); pk = (w[m] * y[m]).sum() / Wk
        z = np.where(m, w * (y - pk) / Wk, 0.0)
        tot = np.bincount(codes, weights=z, minlength=G)
        p.append(pk); scores.append(tot)
    S = np.array(scores); cov = G / (G - 1) * (S @ S.T)
    return np.array(p), cov


# ---- prevalencia global
for d_ in ["ia_total", "ia_grave"]:
    y = df[d_].to_numpy(float); p, cov = cell_stats([np.ones(n, bool)], y)
    rep = t1[t1.variavel == "Total"].iloc[0]
    add(f"overall weighted prevalence {d_} (%)", p[0] * 100, rep[f"{d_}_pct"], 1e-6, "%")
    se_ = float(np.sqrt(cov[0, 0])); sl = se_ / (p[0] * (1 - p[0])); lg = np.log(p[0] / (1 - p[0]))          # IC95% na escala logit (mesma convencao do artigo)
    add(f"overall weighted prevalence {d_} 95% CI lower (%)", 100 / (1 + np.exp(-(lg - Z * sl))), rep[f"{d_}_lo"], 1e-6, "%")
    add(f"overall weighted prevalence {d_} 95% CI upper (%)", 100 / (1 + np.exp(-(lg + Z * sl))), rep[f"{d_}_hi"], 1e-6, "%")

# ---- pares raca x renda e raca x escolaridade (celulas: 00, 10, 01, 11)
black = df["negra"].to_numpy(bool)
ses = {"Race x Income": df["renda_q1"].to_numpy(bool), "Race x Education": df["sem_fund"].to_numpy(bool)}
for par, s in ses.items():
    for d_ in ["ia_total", "ia_grave"]:
        y = df[d_].to_numpy(float)
        masks = [~black & ~s, black & ~s, ~black & s, black & s]
        p, cov = cell_stats(masks, y)
        r = t2[t2.par.str.startswith(par) & (t2.desfecho == d_)].iloc[0]; tag = f"{par}/{d_}"
        for k, nm in enumerate(["p00", "p10", "p01", "p11"]):
            add(f"{tag}: prevalence {nm} (%)", p[k] * 100, r[nm], 1e-6, "%")
        p00, p10, p01, p11 = p
        pr10, pr01, pr11 = p10 / p00, p01 / p00, p11 / p00
        A = p11 - p10 - p01 + p00; reri = A / p00
        add(f"{tag}: PR (Black only)", pr10, r.rr10, 1e-6); add(f"{tag}: PR (SES only)", pr01, r.rr01, 1e-6); add(f"{tag}: PR (both)", pr11, r.rr11, 1e-6)
        add(f"{tag}: RERI", reri, r.reri, 1e-6)
        add(f"{tag}: expected RERI", (pr10 - 1) * (pr01 - 1), r.reri_esperado_nulo_mult, 1e-6)
        ror = pr11 / (pr10 * pr01); add(f"{tag}: ratio of PRs", ror, r.ror, 1e-6)
        add(f"{tag}: joint difference (pp)", (p11 - p00) * 100, r.p11 - r.p00, 1e-6, "pp")
        add(f"{tag}: interaction contrast (pp)", A * 100, r.p11 - r.p10 - r.p01 + r.p00, 1e-6, "pp")
        add(f"{tag}: interaction contrast = RERI x p00 (pp)", reri * p00 * 100, A * 100, 1e-9, "pp")
        # delta method independente: RERI = A/p00 ; gradiente em (p00,p10,p01,p11)
        g = np.array([(p00 - A) / p00 ** 2, -1 / p00, -1 / p00, 1 / p00])
        se = float(np.sqrt(g @ cov @ g))
        add(f"{tag}: RERI 95% CI lower (independent linearisation)", reri - Z * se, r.reri_lo_delta, 0.02)
        add(f"{tag}: RERI 95% CI upper (independent linearisation)", reri + Z * se, r.reri_hi_delta, 0.02)
        # razao de RPs: log ROR = log p11 + log p00 - log p10 - log p01
        gl = np.array([1 / p00, -1 / p10, -1 / p01, 1 / p11]); sel = float(np.sqrt(gl @ cov @ gl))
        add(f"{tag}: ratio of PRs 95% CI lower", np.exp(np.log(ror) - Z * sel), r.ror_lo, 0.005)
        add(f"{tag}: ratio of PRs 95% CI upper", np.exp(np.log(ror) + Z * sel), r.ror_hi, 0.005)
        for k, nm in [(1, "rr10"), (2, "rr01"), (3, "rr11")]:
            gk = np.zeros(4); gk[k] = 1 / p[k]; gk[0] = -1 / p00; sek = float(np.sqrt(gk @ cov @ gk))
            add(f"{tag}: PR {nm} 95% CI lower", np.exp(np.log(p[k] / p00) - Z * sek), r[nm + "_lo"], 0.01)
            add(f"{tag}: PR {nm} 95% CI upper", np.exp(np.log(p[k] / p00) + Z * sek), r[nm + "_hi"], 0.01)


# ---- Poisson ponderado por IRLS escrito a mao (RP ajustada e cluster-robusto)
def poisson_irls(X, y, wt, groups, iters=50):
    beta = np.zeros(X.shape[1]); beta[0] = np.log(np.average(y, weights=wt))
    for _ in range(iters):
        mu = np.exp(X @ beta); W = wt * mu; z = X @ beta + (y - mu) / mu
        XtWX = X.T @ (X * W[:, None]); new = np.linalg.solve(XtWX, X.T @ (W * z))
        if np.max(np.abs(new - beta)) < 1e-10: beta = new; break
        beta = new
    mu = np.exp(X @ beta); W = wt * mu; XtWX = X.T @ (X * W[:, None]); bread = np.linalg.inv(XtWX)
    sc = X * (wt * (y - mu))[:, None]
    codes_g, ug = pd.factorize(groups); Gg = len(ug)
    S = np.zeros((Gg, X.shape[1]))
    np.add.at(S, codes_g, sc)
    meat = S.T @ S
    N, k = X.shape
    corr = Gg / (Gg - 1) * (N - 1) / (N - k)                     # mesma correcao de amostra pequena do statsmodels
    V = bread @ meat @ bread * corr
    return beta, np.sqrt(np.diag(V))


def design(sub, cols_extra):
    parts = [np.ones(len(sub))] + [sub[c].to_numpy(float) for c in cols_extra]
    return np.column_stack(parts)


df["renda_cat"] = np.select([df.renda_q1 == 1, df.renda_q2 == 1, df.renda_q3 == 1, df.renda_q4 == 1], ["q1", "q2", "q3", "q4"], default="q5")
inc_dummies = ["renda_q1", "renda_q2", "renda_q3", "renda_q4"]
edu_dummies = ["sem_fund", "fund_med", "medio_comp"]
for band in ["q1", "q5"]:
    for d_ in ["ia_total", "ia_grave"]:
        sub = df[df.renda_cat == band]
        wt = (sub["peso"] / sub["peso"].mean()).to_numpy(float)
        X = design(sub, ["negra", "mulher", "rural"] + edu_dummies)
        b, se = poisson_irls(X, sub[d_].to_numpy(float), wt, sub["upa"].to_numpy())
        r = t6[(t6.exposicao == "negra") & (t6.estratificado_por == "renda") & (t6.estrato == band) & (t6.desfecho == d_)].iloc[0]
        tag = f"adjusted PR Black, income band {band}, {d_}"
        add(tag, np.exp(b[1]), r.rr_ajustado, 0.002); add(tag + " CI lower", np.exp(b[1] - Z * se[1]), r.lo, 0.005); add(tag + " CI upper", np.exp(b[1] + Z * se[1]), r.hi, 0.005)

# diferenca absoluta bruta (Black - non-Black) por faixa de renda, com EP por linearizacao (grupos tratados como independentes, como no CSV)
for band in ["q1", "q2", "q3", "q4", "q5"]:
    inb = (df.renda_cat == band).to_numpy()
    for d_ in ["ia_total", "ia_grave"]:
        y = df[d_].to_numpy(float)
        p, cov = cell_stats([inb & black, inb & ~black], y)
        dif = (p[0] - p[1]) * 100; se = float(np.sqrt(cov[0, 0] + cov[1, 1])) * 100
        r = t6[(t6.exposicao == "negra") & (t6.estratificado_por == "renda") & (t6.estrato == band) & (t6.desfecho == d_)].iloc[0]
        tag = f"crude difference Black - non-Black, income band {band}, {d_} (pp)"
        add(tag, dif, r.dif_pp, 1e-6, "pp"); add(tag + " CI lower", dif - Z * se, r.dif_pp_lo, 0.05, "pp"); add(tag + " CI upper", dif + Z * se, r.dif_pp_hi, 0.05, "pp")

# atenuacao (raca): bruto, +renda, +renda e demais (ia_total)
d_ = "ia_total"; wt = (df["peso"] / df["peso"].mean()).to_numpy(float); yv = df[d_].to_numpy(float); grp = df["upa"].to_numpy()
b0, _ = poisson_irls(design(df, ["negra"]), yv, wt, grp)
b1, _ = poisson_irls(design(df, ["negra"] + inc_dummies), yv, wt, grp)
b2, se2 = poisson_irls(design(df, ["negra", "mulher", "rural", "sem_fund"] + inc_dummies), yv, wt, grp)   # especificacao do script atenuacao: educacao binaria (sem_fund)
b2_4cat, _ = poisson_irls(design(df, ["negra", "mulher", "rural"] + edu_dummies + inc_dummies), yv, wt, grp)   # variante: educacao em 4 categorias (so' informativo)
ref = lambda esp: aten[(aten.variavel == "Negra") & (aten.especificacao == esp) & (aten.desfecho == d_)].iloc[0]
add("crude PR Black (any)", np.exp(b0[1]), ref("bruto").rr, 0.002); add("PR Black adjusted for income band (any)", np.exp(b1[1]), ref("so_renda").rr, 0.002)
add("PR Black fully adjusted (any); covariates as in atenuacao script: income bands + woman + rural + binary low education", np.exp(b2[1]), ref("renda_e_demais").rr, 0.002)
rows.append({"item": "INFO: same PR with education in four categories (not the reported specification)", "independent": float(np.exp(b2_4cat[1])), "reported_in_csv": float(ref("renda_e_demais").rr), "abs_diff": abs(float(np.exp(b2_4cat[1])) - float(ref("renda_e_demais").rr)), "tolerance": np.nan, "status": "INFO", "unit": "specification sensitivity, not a discrepancy"})
add("attenuation of crude log PR by income alone (%)", (1 - b1[1] / b0[1]) * 100, ref("so_renda").atenuacao_pct, 0.05, "%")

# ---- MAIHDA: aritmetica VPC/PCV e AUC independente
for dd in ["ia_total", "ia_grave"]:
    r = m1.loc[dd]
    add(f"MAIHDA VPC null from sigma2 ({dd}) (%)", r.sigma2_nulo / (r.sigma2_nulo + np.pi ** 2 / 3) * 100, r.vpc_nulo * 100, 1e-6, "%")
    add(f"MAIHDA PCV from sigma2 ({dd}) (%)", (r.sigma2_nulo - r.sigma2_B) / r.sigma2_nulo * 100, r.pcv * 100, 1e-6, "%")
def auc_pandas(y, score):
    """AUC = estatistica de Mann-Whitney com postos medios (pandas), implementacao independente da usada em ms_numeros"""
    r = pd.Series(score).rank(method="average").to_numpy(); yy = np.asarray(y).astype(bool)
    n1 = yy.sum(); n0 = (~yy).sum()
    return (r[yy].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


m3 = pd.read_csv(D / "m3_maihda_estratos.csv"); dm = pd.read_csv(BASE / "dados" / "dados_maihda_2023.csv", usecols=["estrato", "ia_total", "ia_grave"])
m4 = pd.read_csv(D / "m4_auc.csv").set_index("desfecho")
for dd in ["ia_total", "ia_grave"]:
    mm = m3[m3.desfecho == dd].set_index("estrato")["p_completo"]
    add(f"AUC stratum predictions {dd} (independent Mann-Whitney)", auc_pandas(dm[dd], dm["estrato"].map(mm).to_numpy()), float(m4.loc[dd, "auc_p_completo"]), 1e-9)
    add(f"n strata in MAIHDA data ({dd})", dm["estrato"].nunique(), float(m1.loc[dd, "n_estratos"]), 0)

res = pd.DataFrame(rows); res.to_csv(OUT / "F_independent_verification.csv", index=False, encoding="utf-8-sig")
print(res.groupby("status").size().to_string())
print(res[~res.status.isin(["PASS"])].to_string())
print("max abs diff (PASS rows):", res[res.status == "PASS"].abs_diff.max())
