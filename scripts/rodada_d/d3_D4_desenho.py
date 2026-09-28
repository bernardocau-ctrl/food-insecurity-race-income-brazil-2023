# -*- coding: utf-8 -*-
"""
d3_D4_desenho.py: D-4. Estima os principais estimandos sob tres configuracoes de variancia (A, B, C; ver PROTOCOLO_RODADA_D.md)
e compara com os valores ORIGINAIS publicados (dados/v2_20260925/t1_descritiva.csv e t2_pares.csv).
Tambem exporta a entrada e os erros-padrao do motor para a validacao independente em R (d3b_validacao_R_survey.R).
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *
from d1_motor import *
from d2_dados import Dados

D = Dados(); Rn = D.W.shape[1]
OUT = []
CFG = {"A": "pesos + UPA (configuracao antiga; linearizacao)", "B": "pesos + UPA + Estrato (linearizacao estratificada)", "C": "200 pesos replicados (bootstrap Rao-Wu-Yue; mse; R-1)"}


def cells_block(pair, ses, y_name, mask=None, tag="", ses_label=""):
    y = D.y[y_name]; cell = D.cell(ses)
    th = cell_theta(D.w, y, cell, mask); est = derived(th)
    Zm, _ = influence(D.w, y, cell, mask); T = psu_totals(Zm, D.upa, D.n_psu)
    seA = se_delta(th, cov_psu_only(T)); VB, nl = cov_strat(T, D.strat_of_psu); seB = se_delta(th, VB)
    ths = np.array([cell_theta(D.W[:, r], y, cell, mask) for r in range(Rn)]); ders = derived(ths)
    fail = int((~np.isfinite(ders)).any(1).sum()); seC = np.sqrt(((ders - est) ** 2).sum(0) / (Rn - 1))
    n_cell = np.bincount(cell if mask is None else cell[mask], minlength=4)
    for cfg, se in (("A", seA), ("B", seB), ("C", seC)):
        for q, (e, lo, hi, s) in ci_from(est, se).items():
            OUT.append({"grupo": "quatro_celulas", "par": pair, "desfecho": y_name, "config": cfg, "quantidade": q, "estimativa": e, "ic_inf": lo, "ic_sup": hi, "erro_padrao_escala_do_ic": s,
                        "n_p00": n_cell[0], "n_p10": n_cell[1], "n_p01": n_cell[2], "n_p11": n_cell[3], "replicacoes_com_falha": fail if cfg == "C" else 0, "estratos_com_1_UPA": nl if cfg == "B" else 0})
    return est, {"A": seA, "B": seB, "C": seC}, th


def prev_block(label, y_name, mask):
    y = D.y[y_name]; m = mask; w = D.w; p = np.sum(w[m] * y[m]) / np.sum(w[m])
    z = np.zeros(D.n); z[m] = w[m] * (y[m] - p) / np.sum(w[m]); T = psu_totals(z[:, None], D.upa, D.n_psu)
    seA = np.sqrt(cov_psu_only(T)[0, 0]); VB, _ = cov_strat(T, D.strat_of_psu); seB = np.sqrt(VB[0, 0])
    pr = np.array([np.sum(D.W[m, r] * y[m]) / np.sum(D.W[m, r]) for r in range(Rn)]); seC = np.sqrt(((pr - p) ** 2).sum() / (Rn - 1))
    for cfg, se in (("A", seA), ("B", seB), ("C", seC)):
        lo, hi = prev_logit_ci(p, se)
        OUT.append({"grupo": "prevalencia", "par": label, "desfecho": y_name, "config": cfg, "quantidade": "prevalencia_pct", "estimativa": p * 100, "ic_inf": lo * 100, "ic_sup": hi * 100, "erro_padrao_escala_do_ic": se / (p * (1 - p)),
                    "n_p00": int(m.sum()), "n_p10": None, "n_p01": None, "n_p11": None, "replicacoes_com_falha": 0, "estratos_com_1_UPA": 0})


ses_i = D.ses_le(1); ses_e = D.ses_edu()
for y_name in ("ia_total", "ia_grave"):
    cells_block("raca_x_renda(<=1/4 SM)", ses_i, y_name); cells_block("raca_x_escolaridade(sem/fund. incompleto)", ses_e, y_name)
    prev_block("Total", y_name, np.ones(D.n, bool))
    prev_block("nao negra", y_name, D.negra == 0); prev_block("negra (preta+parda)", y_name, D.negra == 1)
    for k, lab in zip([1, 2, 3, 4], ["q1(<=1/4)", "q2(>1/4-1/2)", "q3(>1/2-1)", "q4(>1-2)"]): prev_block("renda " + lab, y_name, D.vdi == k)
    prev_block("renda q5(>2, inclui codigo 9)", y_name, np.isin(D.vdi, [5, 6, 7, 9]))
res = pd.DataFrame(OUT); res.to_csv(OUTD / "D4_estimativas_por_configuracao.csv", index=False, encoding="utf-8-sig")

# ---------------- concordancia com os valores originais publicados
t2 = pd.read_csv(PUBLISHED / "t2_pares.csv"); t1 = pd.read_csv(PUBLISHED / "t1_descritiva.csv")
PAR2 = {"raca_x_renda(<=1/4 SM)": "Race x Income (<= 1/4 MW per capita)", "raca_x_escolaridade(sem/fund. incompleto)": "Race x Education (<= incomplete primary)"}
PUB = {"rr10": ("rr10", "rr10_lo", "rr10_hi"), "rr01": ("rr01", "rr01_lo", "rr01_hi"), "rr11": ("rr11", "rr11_lo", "rr11_hi"), "reri": ("reri", "reri_lo_delta", "reri_hi_delta"),
       "ror": ("ror", "ror_lo", "ror_hi"), "reri_esperado": ("reri_esperado_nulo_mult", None, None), "p00": ("p00", None, None), "p10": ("p10", None, None), "p01": ("p01", None, None), "p11": ("p11", None, None)}
T1MAP = {"Total": ("Total", "Brasil"), "nao negra": ("Cor/raca", "nao negra"), "negra (preta+parda)": ("Cor/raca", "negra (preta+parda)"), "renda q1(<=1/4)": ("Renda pc", "q1"), "renda q2(>1/4-1/2)": ("Renda pc", "q2"),
         "renda q3(>1/2-1)": ("Renda pc", "q3"), "renda q4(>1-2)": ("Renda pc", "q4"), "renda q5(>2, inclui codigo 9)": ("Renda pc", "q5")}
rows = []
for (grupo, par, y, q), g in res.groupby(["grupo", "par", "desfecho", "quantidade"], sort=False):
    g = g.set_index("config"); pub = None
    if grupo == "quatro_celulas" and q in PUB:
        r = t2[(t2.par == PAR2[par]) & (t2.desfecho == y)].iloc[0]; c = PUB[q]; pub = (r[c[0]], r[c[1]] if c[1] else np.nan, r[c[2]] if c[2] else np.nan)
    if grupo == "prevalencia":
        v, cat = T1MAP[par]; r = t1[(t1.variavel == v) & (t1.categoria == cat)].iloc[0]; k = "ia_total" if y == "ia_total" else "ia_grave"
        pub = (r[f"{k}_pct"], r[f"{k}_lo"], r[f"{k}_hi"])
    row = {"grupo": grupo, "par": par, "desfecho": y, "quantidade": q}
    if pub: row.update({"pub_est": pub[0], "pub_lo": pub[1], "pub_hi": pub[2]})
    for cfg in "ABC": row.update({f"{cfg}_est": g.loc[cfg, "estimativa"], f"{cfg}_lo": g.loc[cfg, "ic_inf"], f"{cfg}_hi": g.loc[cfg, "ic_sup"]})
    for cfg in "BC":
        row[f"largura_{cfg}_sobre_A"] = (g.loc[cfg, "ic_sup"] - g.loc[cfg, "ic_inf"]) / (g.loc["A", "ic_sup"] - g.loc["A", "ic_inf"])
        row[f"dif_abs_lo_{cfg}_menos_A"] = g.loc[cfg, "ic_inf"] - g.loc["A", "ic_inf"]; row[f"dif_abs_hi_{cfg}_menos_A"] = g.loc[cfg, "ic_sup"] - g.loc["A", "ic_sup"]
    if pub:
        row["dif_abs_est_A_menos_pub"] = row["A_est"] - pub[0]; row["dif_rel_est_A_vs_pub_pct"] = (row["A_est"] / pub[0] - 1) * 100 if pub[0] else np.nan
        if not np.isnan(pub[1]):
            row["dif_abs_lo_A_menos_pub"] = row["A_lo"] - pub[1]; row["dif_abs_hi_A_menos_pub"] = row["A_hi"] - pub[2]
            row["dif_rel_lo_A_vs_pub_pct"] = (row["A_lo"] / pub[1] - 1) * 100; row["dif_rel_hi_A_vs_pub_pct"] = (row["A_hi"] / pub[2] - 1) * 100
    for cfg in "BC":
        row[f"dif_rel_lo_{cfg}_vs_A_pct"] = (g.loc[cfg, "ic_inf"] / g.loc["A", "ic_inf"] - 1) * 100 if g.loc["A", "ic_inf"] else np.nan
        row[f"dif_rel_hi_{cfg}_vs_A_pct"] = (g.loc[cfg, "ic_sup"] / g.loc["A", "ic_sup"] - 1) * 100 if g.loc["A", "ic_sup"] else np.nan
        row[f"estimativa_igual_A_{cfg}"] = bool(abs(g.loc[cfg, "estimativa"] - g.loc["A", "estimativa"]) < 1e-9 * max(1, abs(g.loc["A", "estimativa"])))
    rows.append(row)
conc = pd.DataFrame(rows); conc.to_csv(OUTD / "D4_concordancia_estimativas_e_ICs.csv", index=False, encoding="utf-8-sig")

# ---------------- exportacao para validacao independente em R
ex = pd.DataFrame({"UPA": D.df["UPA"], "Estrato": D.df["Estrato"], "V1028": D.w, "y_any": D.y["ia_total"], "y_sev": D.y["ia_grave"], "negra": D.negra, "cell_inc": D.cell(ses_i), "cell_edu": D.cell(ses_e)})
ex.to_csv(CACHE / "R_input.csv", index=False)
D.W.astype("<f8").tofile(CACHE / "R_pesos_replicados.bin")
eng = res[res.grupo == "quatro_celulas"].copy(); eng.to_csv(OUTD / "D4_motor_python_para_validacao.csv", index=False, encoding="utf-8-sig")
# resumo
def bmax(cfg, col): return conc[[col]].abs().max().iloc[0]
sm = {"estimativas_pontuais_iguais_entre_A_B_C": bool(conc[["estimativa_igual_A_B", "estimativa_igual_A_C"]].all().all()),
      "max_dif_abs_estimativa_A_vs_publicado": float(conc["dif_abs_est_A_menos_pub"].abs().max()),
      "max_dif_rel_pct_IC_A_vs_publicado_PRs_e_RERI": float(conc[conc.quantidade.isin(["rr10", "rr01", "rr11", "reri", "ror"])][["dif_rel_lo_A_vs_pub_pct", "dif_rel_hi_A_vs_pub_pct"]].abs().max().max()),
      "razao_largura_IC_B_sobre_A_mediana": float(conc["largura_B_sobre_A"].median()), "razao_largura_IC_C_sobre_A_mediana": float(conc["largura_C_sobre_A"].median()),
      "razao_largura_IC_B_sobre_A_min_max": [float(conc["largura_B_sobre_A"].min()), float(conc["largura_B_sobre_A"].max())], "razao_largura_IC_C_sobre_A_min_max": [float(conc["largura_C_sobre_A"].min()), float(conc["largura_C_sobre_A"].max())],
      "replicacoes_com_falha_max": int(res["replicacoes_com_falha"].max())}
import json
(OUTD / "D4_resumo.json").write_text(json.dumps(sm, indent=1), encoding="utf-8"); print(json.dumps(sm, indent=1))
log_execucao("d3_D4_desenho.py", sm)
