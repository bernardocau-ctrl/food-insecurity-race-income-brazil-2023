# -*- coding: utf-8 -*-
"""
d4b_D1_D2.py
D-2: ICs dos componentes absolutos da decomposicao e da participacao percentual (configuracoes A, B e C; principal = a de principal.json).
D-1: analise secundaria padronizada (g-computation) raca/cor x renda (<=1/4 SM), covariaveis: sexo registrado, escolaridade (4), residencia.
Nao altera exposicao, desfecho, populacao ou pesos.
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
COMP = ["comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct"]
ses_i = D.ses_le(1); ses_e = D.ses_edu()
rows = []; diag = []
for pair, ses in (("raca_x_renda(<=1/4 SM)", ses_i), ("raca_x_escolaridade(sem/fund. incompleto)", ses_e)):
    for y_name in ("ia_total", "ia_grave"):
        r = run_raw(D, ses, y_name); est = r["est"]
        for cfg in "ABC":
            ci = ci_from(est, r["se"][cfg])
            for q in COMP:
                e, lo, hi, s = ci[q]
                rows.append({"par": pair, "desfecho": y_name, "config": cfg, "principal": cfg == PRINC, "quantidade": q, "estimativa": e, "ic_inf": lo, "ic_sup": hi, "erro_padrao": s})
        # diagnostico da participacao (replicas)
        dc = r["ders"]; j = dc[:, DER.index("conjunta_pp")]; sh = dc[:, DER.index("participacao_pct")]; sh0 = est[DER.index("participacao_pct")]; j0 = est[DER.index("conjunta_pp")]
        sej = r["se"]["C"][DER.index("conjunta_pp")]; lo_j = j0 - Z * sej
        crit_a = bool(lo_j > 0 and sej / abs(j0) < 0.2); frac_out = float((np.abs(sh) > 3 * abs(sh0)).mean())
        crit_b = bool(frac_out == 0)
        diag.append({"par": pair, "desfecho": y_name, "conjunta_pp": j0, "conjunta_ic_inf": lo_j, "cv_conjunta": sej / abs(j0), "criterio_a_conjunta_positiva_e_cv<0.2": crit_a,
                     "participacao_pct": sh0, "participacao_rep_min": float(sh.min()), "participacao_rep_max": float(sh.max()), "participacao_rep_p2.5": float(np.percentile(sh, 2.5)), "participacao_rep_p97.5": float(np.percentile(sh, 97.5)),
                     "fracao_replicas_|part|>3x|estimativa|": frac_out, "criterio_b_sem_caudas_extremas": crit_b, "regra_do_protocolo_permite_reportar_IC_da_participacao": bool(crit_a and crit_b),
                     "denominador_replicado_min": float(j.min()), "replicacoes_com_falha": r["fail"]})
d2 = pd.DataFrame(rows); d2.to_csv(OUTD / "D2_componentes_absolutos_IC.csv", index=False, encoding="utf-8-sig")
dg = pd.DataFrame(diag); dg.to_csv(OUTD / "D2_diagnostico_participacao.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- D-1
srows = []; coefs = []; cmp_rows = []; info = {}
NAMES = ["intercepto", "celula_10_so_raca", "celula_01_so_renda", "celula_11_ambos", "sexo_mulher", "escol_fund_med", "escol_medio_comp", "escol_superior", "rural"]
for y_name in ("ia_total", "ia_grave"):
    raw = run_raw(D, ses_i, y_name); st = run_std(D, ses_i, y_name)
    info[y_name] = {"fit_convergiu": not st["nonconv_full"], "iteracoes": st["iter_full"], "replicas_nao_convergiram": st["nonconv_reps"], "replicas_com_falha": st["fail"], "n_celulas": [int(x) for x in st["n_cell"]]}
    ciS = ci_from(st["est"], st["se"]["C"]); ciR = ci_from(raw["est"], raw["se"]["C"])
    for q in [x for x in DER if not x.startswith("log_")]:
        e, lo, hi, s = ciS[q]; er, lor, hir, sr = ciR[q]
        # diferenca padronizado - bruto: pareada nas replicas
        i = DER.index(q); dd = st["ders"][:, i] - raw["ders"][:, i]; d0 = st["est"][i] - raw["est"][i]
        sed = np.sqrt(np.nansum((dd - d0) ** 2) / (Rn - 1))
        srows.append({"desfecho": y_name, "quantidade": q, "bruto_est": er, "bruto_lo": lor, "bruto_hi": hir, "padronizado_est": e, "padronizado_lo": lo, "padronizado_hi": hi,
                      "dif_padronizado_menos_bruto": d0, "dif_ic_inf": d0 - Z * sed, "dif_ic_sup": d0 + Z * sed, "config_variancia": "C (pesos replicados; modelo reajustado em cada replica)"})
    b = st["coef"]; bse = np.sqrt(np.nansum((st["coef_reps"] - b) ** 2, 0) / (Rn - 1))
    for nm, bb, ss in zip(NAMES, b, bse): coefs.append({"desfecho": y_name, "termo": nm, "coef_logit": bb, "erro_padrao_replicas": ss, "OR": np.exp(bb), "OR_lo": np.exp(bb - Z * ss), "OR_hi": np.exp(bb + Z * ss)})
S = pd.DataFrame(srows); S.to_csv(OUTD / "D1_padronizado_vs_bruto_raca_renda.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(coefs).to_csv(OUTD / "D1_coeficientes_modelo_logistico.csv", index=False, encoding="utf-8-sig")
# composicao das celulas (justificativa das covariaveis; descritiva, pesos finais)
comp = []
cell = D.cell(ses_i); lab = {0: "nao negra, >1/4 SM (ref.)", 1: "negra, >1/4 SM", 2: "nao negra, <=1/4 SM", 3: "negra, <=1/4 SM"}
for k in range(4):
    m = cell == k; w = D.w[m]; tot = w.sum(); f = lambda a: float((w * a[m]).sum() / tot * 100)
    comp.append({"celula": lab[k], "n": int(m.sum()), "pct_mulher": f(D.female), "pct_rural": f(D.rural), "pct_sem_fund_ou_menos": f((D.edu4 == 0).astype(float)), "pct_fund_med": f((D.edu4 == 1).astype(float)),
                 "pct_medio_completo": f((D.edu4 == 2).astype(float)), "pct_superior": f((D.edu4 == 3).astype(float))})
w = D.w; tot = w.sum(); comp.append({"celula": "todos os domicilios (populacao-padrao)", "n": D.n, "pct_mulher": float((w * D.female).sum() / tot * 100), "pct_rural": float((w * D.rural).sum() / tot * 100),
                                   **{k2: float((w * (D.edu4 == i).astype(float)).sum() / tot * 100) for i, k2 in enumerate(["pct_sem_fund_ou_menos", "pct_fund_med", "pct_medio_completo", "pct_superior"])}})
pd.DataFrame(comp).to_csv(OUTD / "D1_composicao_das_celulas.csv", index=False, encoding="utf-8-sig")
(OUTD / "D1_D2_resumo.json").write_text(json.dumps({"principal": PRINC, "D1": info}, indent=1), encoding="utf-8")
print(json.dumps(info, indent=1)); print(dg.to_string())
log_execucao("d4b_D1_D2.py", {"principal": PRINC, "D1": info})
