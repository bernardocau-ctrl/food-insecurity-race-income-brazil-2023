# -*- coding: utf-8 -*-
"""
d5_D3_D5.py
D-3: sensibilidade ao ponto de corte de renda (<=1/4, <=1/2, <=1 SM per capita), contraste bruto raca/cor x renda. EXPLORATORIA.
D-5: repeticao dos estimandos principais excluindo os domicilios com raca/cor ignorada (V2010=9) e/ou renda ignorada (VDI5009=9).
Configuracao de variancia dos ICs: a de principal.json (C).
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *
from d1_motor import *
from d2_dados import Dados

D = Dados(); Rn = D.W.shape[1]
PRINC = json.loads((OUTD / "principal.json").read_text(encoding="utf-8"))["principal"]
Q = [x for x in DER if not x.startswith("log_")]
CUT = {1: "<=1/4 SM (primario)", 2: "<=1/2 SM", 3: "<=1 SM"}

# ---------------------------------------------------------------- D-3
rows = []
for cut, lab in CUT.items():
    ses = D.ses_le(cut)
    for y_name in ("ia_total", "ia_grave"):
        r = run_raw(D, ses, y_name)
        for cfg in "ABC":
            ci = ci_from(r["est"], r["se"][cfg])
            for q in Q:
                e, lo, hi, s = ci[q]
                rows.append({"corte": lab, "desfecho": y_name, "config": cfg, "principal": cfg == PRINC, "quantidade": q, "estimativa": e, "ic_inf": lo, "ic_sup": hi, "erro_padrao": s,
                             "n_ref": int(r["n_cell"][0]), "n_so_raca": int(r["n_cell"][1]), "n_so_renda": int(r["n_cell"][2]), "n_ambos": int(r["n_cell"][3]),
                             "pct_baixa_renda_ponderado": float(D.w[ses == 1].sum() / D.w.sum() * 100), "replicacoes_com_falha": r["fail"] if cfg == "C" else 0})
d3 = pd.DataFrame(rows); d3.to_csv(OUTD / "D3_sensibilidade_corte_renda.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- D-5
keep = ~(D.ign_raca | D.ign_renda)
info = {"n_total": D.n, "n_raca_ignorada": int(D.ign_raca.sum()), "n_renda_ignorada": int(D.ign_renda.sum()), "n_ambos": int((D.ign_raca & D.ign_renda).sum()), "n_excluidos_uniao": int((~keep).sum()), "n_analise_restrita": int(keep.sum())}
rows = []


def add(grupo, par, y_name, e_full, se_full, e_ex, se_ex, names):
    ciF = ci_from(e_full, se_full); ciE = ci_from(e_ex, se_ex)
    for q in names:
        e, lo, hi, s = ciF[q]; e2, lo2, hi2, s2 = ciE[q]
        rows.append({"grupo": grupo, "par": par, "desfecho": y_name, "quantidade": q, "principal_est": e, "principal_lo": lo, "principal_hi": hi, "excluidos_est": e2, "excluidos_lo": lo2, "excluidos_hi": hi2,
                     "dif_abs": e2 - e, "dif_rel_pct": (e2 / e - 1) * 100 if e else np.nan, "meia_largura_IC_principal": (hi - lo) / 2, "dif_abs_sobre_meia_largura": abs(e2 - e) / ((hi - lo) / 2)})


for pair, ses in (("raca_x_renda(<=1/4 SM)", D.ses_le(1)), ("raca_x_escolaridade(sem/fund. incompleto)", D.ses_edu())):
    for y_name in ("ia_total", "ia_grave"):
        a = run_raw(D, ses, y_name); b = run_raw(D, ses, y_name, keep)
        add("quatro_celulas_bruto", pair, y_name, a["est"], a["se"][PRINC], b["est"], b["se"][PRINC], Q)
for y_name in ("ia_total", "ia_grave"):
    a = run_std(D, D.ses_le(1), y_name); b = run_std(D, D.ses_le(1), y_name, keep)
    add("quatro_celulas_padronizado(D-1)", "raca_x_renda(<=1/4 SM)", y_name, a["est"], a["se"]["C"], b["est"], b["se"]["C"], Q)
    info[f"padronizado_{y_name}_replicas_com_falha"] = [a["fail"], b["fail"]]
# prevalencias por categoria (com e sem exclusao; variancia C)
def prev(y_name, m):
    y = D.y[y_name]; p = np.sum(D.w[m] * y[m]) / np.sum(D.w[m]); pr = np.array([np.sum(D.W[m, r] * y[m]) / np.sum(D.W[m, r]) for r in range(Rn)]); se = np.sqrt(((pr - p) ** 2).sum() / (Rn - 1)); return p, se
cats = {"Total": np.ones(D.n, bool), "nao negra": D.negra == 0, "negra (preta+parda)": D.negra == 1, "renda q1(<=1/4)": D.vdi == 1, "renda q2": D.vdi == 2, "renda q3": D.vdi == 3, "renda q4": D.vdi == 4, "renda q5(>2, inclui codigo 9 no principal)": np.isin(D.vdi, [5, 6, 7, 9])}
for y_name in ("ia_total", "ia_grave"):
    for lab, m in cats.items():
        p, s = prev(y_name, m); p2, s2 = prev(y_name, m & keep); lo, hi = prev_logit_ci(p, s); lo2, hi2 = prev_logit_ci(p2, s2)
        rows.append({"grupo": "prevalencia", "par": lab, "desfecho": y_name, "quantidade": "prevalencia_pct", "principal_est": p * 100, "principal_lo": lo * 100, "principal_hi": hi * 100, "excluidos_est": p2 * 100, "excluidos_lo": lo2 * 100, "excluidos_hi": hi2 * 100,
                     "dif_abs": (p2 - p) * 100, "dif_rel_pct": (p2 / p - 1) * 100, "meia_largura_IC_principal": (hi - lo) * 50, "dif_abs_sobre_meia_largura": abs(p2 - p) / ((hi - lo) / 2)})
d5 = pd.DataFrame(rows)
CLASSE = {"prevalencia_pct": "prevalencia (geral e por categoria)", "p00": "prevalencia de celula", "p10": "prevalencia de celula", "p01": "prevalencia de celula", "p11": "prevalencia de celula", "rr10": "PR", "rr01": "PR", "rr11": "PR",
          "reri": "RERI", "reri_esperado": "RERI esperado sob multiplicatividade", "ror": "razao de PRs", "comp_raca_pp": "componente absoluto (pp)", "comp_ses_pp": "componente absoluto (pp)", "interacao_pp": "componente absoluto (pp)",
          "conjunta_pp": "componente absoluto (pp)", "participacao_pct": "participacao percentual da interacao"}
d5["classe"] = d5["quantidade"].map(CLASSE); d5["analise"] = d5["grupo"].map(lambda g: "padronizada" if "padronizado" in g else "bruta")
d5.to_csv(OUTD / "D5_ignorados_comparacao_completa.csv", index=False, encoding="utf-8-sig")
sm = []
for (an, cl), g in d5.groupby(["analise", "classe"]):
    i = g["dif_abs"].abs().idxmax(); j = g["dif_abs_sobre_meia_largura"].idxmax()
    sm.append({"analise": an, "classe": cl, "maior_dif_abs": g.loc[i, "dif_abs"], "onde_maior_dif_abs": f"{g.loc[i, 'par']} | {g.loc[i, 'desfecho']} | {g.loc[i, 'quantidade']}", "unidade": "pp" if cl in ("prevalencia (geral e por categoria)", "prevalencia de celula", "componente absoluto (pp)", "participacao percentual da interacao") else "razao/indice",
               "maior_dif_relativa_pct": g["dif_rel_pct"].abs().max(), "maior_dif_sobre_meia_largura_IC": g.loc[j, "dif_abs_sobre_meia_largura"], "onde_maior_razao": f"{g.loc[j, 'par']} | {g.loc[j, 'desfecho']} | {g.loc[j, 'quantidade']}"})
sm = pd.DataFrame(sm); sm.to_csv(OUTD / "D5_maiores_diferencas_por_classe.csv", index=False, encoding="utf-8-sig")
info["criterio_nao_material(max dif < 10% da meia-largura do IC)"] = bool(sm["maior_dif_sobre_meia_largura_IC"].max() < 0.10)
info["maior_razao_dif_sobre_meia_largura"] = float(sm["maior_dif_sobre_meia_largura_IC"].max())
(OUTD / "D5_resumo.json").write_text(json.dumps(info, indent=1), encoding="utf-8"); print(json.dumps(info, indent=1)); print(sm.round(4).to_string())
log_execucao("d5_D3_D5.py", info)
