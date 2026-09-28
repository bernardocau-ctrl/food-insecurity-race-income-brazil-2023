# -*- coding: utf-8 -*-
"""
d11_regressoes_C.py
Regenera com a configuracao C (200 pesos replicados; bootstrap de Rao-Wu-Yue; V = sum_r (theta_r - theta)^2 / (R - 1), centrado na estimativa completa)
TODAS as tabelas de estimativas ponderadas do Artigo 3 (t1, t2, t3, t4, t5, t6, t7 e a atenuacao), na pasta VERSIONADA dados/v3_rodadaD_C/.
Os CSV historicos (dados/v2_20260925, dados/atenuacao_*.csv) NAO sao tocados. As estimativas pontuais sao recalculadas e conferidas contra as historicas.
Modelos (mesmas especificacoes do codigo original): Poisson ponderado log-link (t3, t5 relativo, t6, t7, atenuacao) e linear ponderado (t5 absoluto).
Cada modelo e' reajustado com cada peso replicado. MAIHDA (m1-m4): copiado sem alteracao (modelo misto NAO ponderado; ver MANIFEST).
"""
import json, shutil, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm, chi2
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *
from d1_motor import *
from d2_dados import Dados

V3 = ART / "dados" / "v3_rodadaD_C"; V3.mkdir(exist_ok=True)
VAR = "C: 200 pesos replicados (bootstrap Rao-Wu-Yue; mse; divisor R-1)"
D = Dados(); Rn = D.W.shape[1]
NEG = D.negra.astype(float); MUL = D.female.astype(float); RUR = D.rural.astype(float)
SEMF = (D.edu4 == 0).astype(float)
EDU3 = np.column_stack([(D.edu4 == k) for k in (1, 2, 3)]).astype(float)                      # fund_med, medio, superior (ref.: sem_fund)
band = np.select([D.vdi == 1, D.vdi == 2, D.vdi == 3, D.vdi == 4], [0, 1, 2, 3], default=4)   # q1..q4; q5 = 5-7 e 9 (codigo original)
RQ = np.column_stack([(band == k) for k in range(4)]).astype(float)                          # renda_q1..q4 (ref.: q5)
RQ1 = RQ[:, 0]
BANDS = ["q1", "q2", "q3", "q4", "q5"]; EDUC = ["sem_fund", "fund_med", "medio_comp", "superior"]
Y = D.y; t_start = time.time(); fails = {"modelos_com_falha_em_replica": 0}


def _clip(e): return np.clip(e, -30, 30)


def poisson(X, y, w, maxit=100, tol=1e-10):
    m = w > 0; X, y, w = X[m], y[m], w[m]; b = np.zeros(X.shape[1]); mu0 = np.average(y, weights=w); b[0] = np.log(mu0) if mu0 > 0 else -10
    for _ in range(maxit):
        eta = _clip(X @ b); mu = np.exp(eta); z = eta + (y - mu) / mu; Wt = w * mu
        bn = np.linalg.solve(X.T @ (X * Wt[:, None]), X.T @ (Wt * z))
        if np.max(np.abs(bn - b)) < tol: return bn
        b = bn
    return b


def linear(X, y, w):
    m = w > 0; X, y, w = X[m], y[m], w[m]; return np.linalg.solve(X.T @ (X * w[:, None]), X.T @ (w * y))


def fit_rep(fn, X, y, mask=None):
    """coeficientes com o peso final e com cada peso replicado (linhas fora da mascara removidas)"""
    if mask is not None: X, y = X[mask], y[mask]; w = D.w[mask]; W = D.W[mask]
    else: w = D.w; W = D.W
    b = fn(X, y, w); B = np.full((Rn, len(b)), np.nan)
    for r in range(Rn):
        try: B[r] = fn(X, y, W[:, r])
        except np.linalg.LinAlgError: fails["modelos_com_falha_em_replica"] += 1
    return b, B


def se_of(b, B): return np.sqrt(np.nansum((B - b) ** 2, 0) / (Rn - 1))
def pz(b, se): return 2 * (1 - norm.cdf(abs(b) / se)) if se > 0 else np.nan
def X_of(*cols): return np.column_stack([np.ones(D.n)] + [c if c.ndim == 2 else c[:, None] for c in cols])


# ---------------------------------------------------------------- t1 (prevalencias por categoria) e prevalencia geral com IC replicado
def prev_rep(y, m):
    p = np.sum(D.w[m] * y[m]) / np.sum(D.w[m]); pr = np.array([np.sum(D.W[m, r] * y[m]) / np.sum(D.W[m, r]) for r in range(Rn)]); se = np.sqrt(((pr - p) ** 2).sum() / (Rn - 1))
    return p, se, pr


def logit_ci(p, se):
    if not (0 < p < 1): return p, p
    lo, hi = prev_logit_ci(p, se); return lo, hi


t1_rows = []
def add_t1(var, cat, m):
    row = {"variavel": var, "categoria": cat, "n": int(m.sum()), "pct_pond_amostra": float(D.w[m].sum() / D.w.sum() * 100)}
    for k, y_name in (("ia_total", "ia_total"), ("ia_grave", "ia_grave")):
        p, se, _ = prev_rep(Y[y_name], m); lo, hi = logit_ci(p, se); row.update({f"{k}_pct": p * 100, f"{k}_lo": lo * 100, f"{k}_hi": hi * 100})
    row["variancia"] = VAR; t1_rows.append(row)
allm = np.ones(D.n, bool)
add_t1("Total", "Brasil", allm)
add_t1("Cor/raca", "nao negra", D.negra == 0); add_t1("Cor/raca", "negra (preta+parda)", D.negra == 1)
add_t1("Sexo", "homem", D.female == 0); add_t1("Sexo", "mulher", D.female == 1)
add_t1("Situacao", "urbano", D.rural == 0); add_t1("Situacao", "rural", D.rural == 1)
for k, c in enumerate(EDUC): add_t1("Instrucao", c, D.edu4 == k)
for k, c in enumerate(BANDS): add_t1("Renda pc", c, band == k)
t1v = pd.DataFrame(t1_rows)

# ---------------------------------------------------------------- t2 (pares) com componentes e IC
PARES = [("Race x Sex (woman)", D.female), ("Race x Education (<= incomplete primary)", D.ses_edu()), ("Race x Income (<= 1/4 MW per capita)", D.ses_le(1)), ("Race x Residence (rural)", D.rural)]
t2_rows = []
for par, ses in PARES:
    for y_name in ("ia_total", "ia_grave"):
        r = run_raw(D, ses, y_name); e = r["est"]; se = r["se"]["C"]; ci_ = ci_from(e, se); g = lambda q: ci_[q]
        i = lambda q: DER.index(q); ror_se = se[i("log_ror")]
        row = {"par": par, "desfecho": y_name, "p00": e[i("p00")], "n00": int(r["n_cell"][0]), "p10": e[i("p10")], "n10": int(r["n_cell"][1]), "p01": e[i("p01")], "n01": int(r["n_cell"][2]), "p11": e[i("p11")], "n11": int(r["n_cell"][3])}
        for q in ("rr10", "rr01", "rr11"): row.update({q: g(q)[0], q + "_lo": g(q)[1], q + "_hi": g(q)[2]})
        row.update({"reri": g("reri")[0], "reri_lo_delta": g("reri")[1], "reri_hi_delta": g("reri")[2], "reri_esperado_nulo_mult": g("reri_esperado")[0], "ror": g("ror")[0], "ror_lo": g("ror")[1], "ror_hi": g("ror")[2],
                    "ror_p": pz(np.log(g("ror")[0]), ror_se)})
        row.update({"reri_esperado_lo": g("reri_esperado")[1], "reri_esperado_hi": g("reri_esperado")[2]})
        for q in ("comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct"): row.update({q: g(q)[0], q + "_lo": g(q)[1], q + "_hi": g(q)[2]})
        row.update({"replicacoes_com_falha": r["fail"], "variancia": VAR}); t2_rows.append(row)
t2v = pd.DataFrame(t2_rows)

# ---------------------------------------------------------------- t3 (modelo conjunto mutuamente ajustado)
t3_rows = []
TERMOS = ["negra", "mulher", "sem_fund", "renda_q1", "rural", "negra:mulher", "negra:sem_fund", "negra:renda_q1", "negra:rural"]
Xj = X_of(NEG, MUL, SEMF, RQ1, RUR, NEG * MUL, NEG * SEMF, NEG * RQ1, NEG * RUR)
for y_name in ("ia_total", "ia_grave"):
    b, B = fit_rep(poisson, Xj, Y[y_name]); se = se_of(b, B)
    for k, t in enumerate(TERMOS, 1):
        t3_rows.append({"desfecho": y_name, "termo": t, "tipo": "interacao" if ":" in t else "principal", "rr": np.exp(b[k]), "lo": np.exp(b[k] - Z * se[k]), "hi": np.exp(b[k] + Z * se[k]), "p": pz(b[k], se[k])})
    idx = [6, 7, 8, 9]
    Vc = (B[:, idx] - b[idx]).T @ (B[:, idx] - b[idx]) / (Rn - 1)                 # centrada na estimativa completa (mse)
    stat = float(b[idx] @ np.linalg.solve(Vc, b[idx])); t3_rows.append({"desfecho": y_name, "termo": "WALD_conjunto_4gl", "tipo": "teste", "rr": stat, "lo": np.nan, "hi": np.nan, "p": float(chi2.sf(stat, 4))})
t3v = pd.DataFrame(t3_rows); t3v["variancia"] = VAR

# ---------------------------------------------------------------- t4 (gradiente de prevalencia) e t5 (modelos do gradiente)
NDES = (MUL + SEMF + RQ1 + RUR).astype(int)
t4_rows = []
for y_name in ("ia_total", "ia_grave"):
    for k in range(5):
        row = {"desfecho": y_name, "n_desv": k}
        for g, nome in ((0, "nao_negra"), (1, "negra")):
            m = (D.negra == g) & (NDES == k); n = int(m.sum())
            if n > 1: p, se, _ = prev_rep(Y[y_name], m); lo, hi = logit_ci(p, se); row.update({f"{nome}_n": n, f"{nome}_pct": p * 100, f"{nome}_lo": lo * 100, f"{nome}_hi": hi * 100})
            else: row.update({f"{nome}_n": n, f"{nome}_pct": np.nan, f"{nome}_lo": np.nan, f"{nome}_hi": np.nan})
        row["diferenca_pp"] = row["negra_pct"] - row["nao_negra_pct"]; row["razao"] = row["negra_pct"] / row["nao_negra_pct"] if row["nao_negra_pct"] else np.nan
        t4_rows.append(row)
t4v = pd.DataFrame(t4_rows); t4v["variancia"] = VAR
t5_rows = []; Xg = X_of(NEG, NDES.astype(float), NEG * NDES)
for y_name in ("ia_total", "ia_grave"):
    b, B = fit_rep(poisson, Xg, Y[y_name]); comb = B[:, 2] + B[:, 3]; s0 = se_of(b, B)[2]; sN = np.sqrt(np.nansum((comb - (b[2] + b[3])) ** 2) / (Rn - 1)); sI = se_of(b, B)[3]
    t5_rows.append({"desfecho": y_name, "escala": "relativa (RR por desvantagem)", "nao_negra": np.exp(b[2]), "nao_negra_lo": np.exp(b[2] - Z * s0), "nao_negra_hi": np.exp(b[2] + Z * s0),
                    "negra": np.exp(b[2] + b[3]), "negra_lo": np.exp(b[2] + b[3] - Z * sN), "negra_hi": np.exp(b[2] + b[3] + Z * sN), "p_diferenca": pz(b[3], sI)})
    b, B = fit_rep(linear, Xg, Y[y_name]); comb = 100 * (B[:, 2] + B[:, 3]); s0 = 100 * se_of(b, B)[2]; sN = np.sqrt(np.nansum((comb - 100 * (b[2] + b[3])) ** 2) / (Rn - 1)); sI = se_of(b, B)[3]
    t5_rows.append({"desfecho": y_name, "escala": "absoluta (pp por desvantagem)", "nao_negra": 100 * b[2], "nao_negra_lo": 100 * b[2] - Z * s0, "nao_negra_hi": 100 * b[2] + Z * s0,
                    "negra": 100 * (b[2] + b[3]), "negra_lo": 100 * (b[2] + b[3]) - Z * sN, "negra_hi": 100 * (b[2] + b[3]) + Z * sN, "p_diferenca": pz(b[3], sI)})
t5v = pd.DataFrame(t5_rows); t5v["variancia"] = VAR

# ---------------------------------------------------------------- t6 (PR ajustada e diferenca absoluta por estrato)
t6_rows = []
def estrato(rot, cat, m, expos, cov_cols):
    """expos: vetor 0/1; cov_cols: colunas de covariaveis (matriz n x q); mascara m"""
    for y_name in ("ia_total", "ia_grave"):
        y = Y[y_name]; X = X_of(expos, cov_cols); b, B = fit_rep(poisson, X, y, m); se = se_of(b, B)
        e1 = m & (expos == 1); e0 = m & (expos == 0)
        p1, s1, r1 = prev_rep(y, e1); p0, s0, r0 = prev_rep(y, e0); l1, h1 = logit_ci(p1, s1); l0, h0 = logit_ci(p0, s0)
        dd = (r1 - r0) - (p1 - p0); sdif = np.sqrt((dd ** 2).sum() / (Rn - 1))
        t6_rows.append({"exposicao": exposname[id(expos)], "estratificado_por": rot, "estrato": cat, "desfecho": y_name, "n": int(m.sum()), "prev_exposto": p1 * 100, "prev_exposto_lo": l1 * 100, "prev_exposto_hi": h1 * 100,
                        "prev_nao_exposto": p0 * 100, "prev_nao_exposto_lo": l0 * 100, "prev_nao_exposto_hi": h0 * 100, "dif_pp": (p1 - p0) * 100, "dif_pp_lo": (p1 - p0 - Z * sdif) * 100, "dif_pp_hi": (p1 - p0 + Z * sdif) * 100,
                        "rr_ajustado": np.exp(b[1]), "lo": np.exp(b[1] - Z * se[1]), "hi": np.exp(b[1] + Z * se[1]), "p": pz(b[1], se[1])})
exposname = {id(NEG): "negra", id(MUL): "mulher"}
for k, c in enumerate(BANDS):
    m = band == k
    estrato("renda", c, m, NEG, np.column_stack([MUL, EDU3, RUR])); estrato("renda", c, m, MUL, np.column_stack([NEG, EDU3, RUR]))
for k, c in enumerate(EDUC): estrato("instrucao", c, D.edu4 == k, NEG, np.column_stack([MUL, RQ, RUR]))
for g, nome in ((0, "nao_negra"), (1, "negra")): estrato("raca", nome, D.negra == g, MUL, np.column_stack([EDU3, RQ, RUR]))
t6v = pd.DataFrame(t6_rows); t6v["variancia"] = VAR

# ---------------------------------------------------------------- t7 (tripla)
t7_rows = []
for mod, M in (("renda_q1", RQ1), ("sem_fund", SEMF)):
    X = X_of(NEG, MUL, M, NEG * MUL, NEG * M, MUL * M, NEG * MUL * M)
    for y_name in ("ia_total", "ia_grave"):
        b, B = fit_rep(poisson, X, Y[y_name]); se = se_of(b, B)
        t7_rows.append({"terceira_dimensao": mod, "desfecho": y_name, "termo": f"negra:mulher:{mod}", "rr": np.exp(b[7]), "lo": np.exp(b[7] - Z * se[7]), "hi": np.exp(b[7] + Z * se[7]), "p": pz(b[7], se[7])})
t7v = pd.DataFrame(t7_rows); t7v["variancia"] = VAR

# ---------------------------------------------------------------- atenuacao
at_rows = []
VARS = [("negra", "Negra", NEG), ("mulher", "Mulher", MUL), ("sem_fund", "Sem instrução", SEMF), ("rural", "Rural", RUR)]
for y_name in ("ia_total", "ia_grave"):
    for var, rot, v in VARS:
        outras = [c for k, _, c in VARS if k != var]
        specs = [("bruto", X_of(v)), ("so_renda", X_of(v, RQ)), ("renda_e_demais", X_of(v, RQ, *outras))]
        res = {}
        for nome, X in specs:
            b, B = fit_rep(poisson, X, Y[y_name]); res[nome] = (b, B)
        b0, B0 = res["bruto"]
        for nome, X in specs:
            b, B = res[nome]; se = se_of(b, B)[1]
            row = {"desfecho": y_name, "variavel": rot, "especificacao": nome, "beta": b[1], "rr": np.exp(b[1]), "ic95_low": np.exp(b[1] - Z * se), "ic95_high": np.exp(b[1] + Z * se), "p_valor": pz(b[1], se)}
            if nome == "bruto": row.update({"atenuacao_pct": 0.0, "atenuacao_lo": np.nan, "atenuacao_hi": np.nan})
            else:
                at = 100 * (1 - b[1] / b0[1]); atr = 100 * (1 - B[:, 1] / B0[:, 1]); sa = np.sqrt(np.nansum((atr - at) ** 2) / (Rn - 1)); row.update({"atenuacao_pct": at, "atenuacao_lo": at - Z * sa, "atenuacao_hi": at + Z * sa})
            at_rows.append(row)
atv = pd.DataFrame(at_rows); atv["variancia"] = VAR

# ---------------------------------------------------------------- escrita e conferencia contra os CSV historicos
files = {"t1_descritiva.csv": t1v, "t2_pares.csv": t2v, "t3_conjunto.csv": t3v, "t4_gradiente_prev.csv": t4v, "t5_gradiente_modelos.csv": t5v, "t6_estratificado.csv": t6v, "t7_tripla.csv": t7v, "atenuacao_renda_raca_sexo_2023.csv": atv}
for n, df in files.items(): df.to_csv(V3 / n, index=False)
manifest = []; cmp_rows = []
HIST = {"t1_descritiva.csv": PUBLISHED, "t2_pares.csv": PUBLISHED, "t3_conjunto.csv": PUBLISHED, "t4_gradiente_prev.csv": PUBLISHED, "t5_gradiente_modelos.csv": PUBLISHED, "t6_estratificado.csv": PUBLISHED, "t7_tripla.csv": PUBLISHED, "atenuacao_renda_raca_sexo_2023.csv": ART / "dados"}
KEYS = {"t1_descritiva.csv": ["variavel", "categoria"], "t2_pares.csv": ["par", "desfecho"], "t3_conjunto.csv": ["desfecho", "termo"], "t4_gradiente_prev.csv": ["desfecho", "n_desv"], "t5_gradiente_modelos.csv": ["desfecho", "escala"],
        "t6_estratificado.csv": ["exposicao", "estratificado_por", "estrato", "desfecho"], "t7_tripla.csv": ["terceira_dimensao", "desfecho"], "atenuacao_renda_raca_sexo_2023.csv": ["desfecho", "variavel", "especificacao"]}
PONTO = {"t1_descritiva.csv": ["n", "pct_pond_amostra", "ia_total_pct", "ia_grave_pct"], "t2_pares.csv": ["p00", "p10", "p01", "p11", "rr10", "rr01", "rr11", "reri", "reri_esperado_nulo_mult", "ror"], "t3_conjunto.csv": ["rr"],
         "t4_gradiente_prev.csv": ["nao_negra_pct", "negra_pct", "diferenca_pp"], "t5_gradiente_modelos.csv": ["nao_negra", "negra"], "t6_estratificado.csv": ["n", "prev_exposto", "prev_nao_exposto", "dif_pp", "rr_ajustado"],
         "t7_tripla.csv": ["rr"], "atenuacao_renda_raca_sexo_2023.csv": ["beta", "rr", "atenuacao_pct"]}
for n, df in files.items():
    h = pd.read_csv(HIST[n] / n); k = KEYS[n]
    m = h.merge(df, on=k, suffixes=("_hist", "_C"), how="outer", indicator=True); assert (m["_merge"] == "both").all(), (n, m["_merge"].value_counts().to_dict())
    for c in PONTO[n]:
        if n == "t3_conjunto.csv" and False: pass
        a, b_ = m[c + "_hist"].astype(float), m[c + "_C"].astype(float)
        if n == "t3_conjunto.csv": msk = m["termo"] != "WALD_conjunto_4gl"; a, b_ = a[msk], b_[msk]
        rel = float((np.abs(a - b_) / np.maximum(np.abs(a), 1e-12)).max()); cmp_rows.append({"arquivo": n, "coluna_de_estimativa_pontual": c, "max_dif_relativa_C_vs_historico": rel, "status": "PASS" if rel < 1e-6 else "REVISAR"})
    manifest.append({"arquivo": n, "origem": "d11_regressoes_C.py (t2: motor d1_motor.run_raw)", "variancia": VAR, "linhas": len(df), "colunas_de_IC": "ver arquivo; coluna 'variancia' identifica a configuracao"})
cmpdf = pd.DataFrame(cmp_rows); cmpdf.to_csv(OUTD / "R11_pontos_C_vs_historico.csv", index=False, encoding="utf-8-sig")
assert (cmpdf.status == "PASS").all(), cmpdf[cmpdf.status != "PASS"]
# MAIHDA: copia sem alteracao (nao ponderado) + auditoria de hash
for n in ["m1_maihda_geral.csv", "m2_maihda_coef.csv", "m3_maihda_estratos.csv", "m4_auc.csv"]:
    shutil.copy2(PUBLISHED / n, V3 / n); manifest.append({"arquivo": n, "origem": "copia sem alteracao de dados/v2_20260925 (MAIHDA, R/lme4)", "variancia": "MAIHDA: modelo misto NAO ponderado, escala logit; sem pesos replicados", "linhas": len(pd.read_csv(V3 / n)), "colunas_de_IC": "IC de perfil de verossimilhanca / Wald (ver relatorio da v1)"})
for m_ in manifest: m_["sha256"] = sha256(V3 / m_["arquivo"])
pd.DataFrame(manifest).to_csv(V3 / "MANIFEST.csv", index=False, encoding="utf-8-sig")
(V3 / "LEIA-ME.md").write_text("# dados/v3_rodadaD_C (versao com variancia da configuracao C)\n\nGerado por `scripts/rodada_d/d11_regressoes_C.py` (25/09/2026). ICs e valores p de todas as estimativas ponderadas vem dos 200 pesos replicados (V1028001-V1028200; bootstrap de Rao, Wu e Yue; V = soma (theta_r - theta)^2 / (R-1), centrado na estimativa completa; z = 1,959964). Estimativas pontuais identicas as de `dados/v2_20260925` (conferido em `rodada_D/R11_pontos_C_vs_historico.csv`). Os arquivos m1-m4 (MAIHDA, nao ponderado) sao copias sem alteracao. Os CSV historicos NAO foram sobrescritos. `MANIFEST.csv` traz SHA-256 e metodo de variancia por arquivo.\nObservacoes: valores p e testes de Wald vem da covariancia das replicas (centrada na estimativa completa); os z-testes usam z normal.\n", encoding="utf-8")
print(cmpdf.groupby("arquivo").max_dif_relativa_C_vs_historico.max().to_string()); print("falhas de replica:", fails, "| segundos:", round(time.time() - t_start))
log_execucao("d11_regressoes_C.py", {"falhas_de_replica": fails["modelos_com_falha_em_replica"], "arquivos": list(files)})
