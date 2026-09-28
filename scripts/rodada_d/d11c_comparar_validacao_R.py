# -*- coding: utf-8 -*-
"""d11c_comparar_validacao_R.py: compara as estimativas e erros-padrao da configuracao C (Python; dados/v3_rodadaD_C e rodada_D/D1) com a implementacao independente em R
(survey::svyglm quasipoisson em desenho replicado; glm quasibinomial para a padronizacao). Saida: rodada_D/R11_comparacao_python_vs_R.csv"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *
V3 = ART / "dados" / "v3_rodadaD_C"; Rr = pd.read_csv(OUTD / "R11_validacao_regressoes_R.csv").set_index("item")
t1 = pd.read_csv(V3 / "t1_descritiva.csv"); t6 = pd.read_csv(V3 / "t6_estratificado.csv"); at = pd.read_csv(V3 / "atenuacao_renda_raca_sexo_2023.csv"); t3 = pd.read_csv(V3 / "t3_conjunto.csv"); s1 = pd.read_csv(OUTD / "D1_padronizado_vs_bruto_raca_renda.csv")
lg = lambda p: np.log(p / (1 - p)); rows = []
def add(item, est_py, se_py):
    e, s = Rr.loc[item, "est"], Rr.loc[item, "se"]
    rows.append({"item": item, "est_python": est_py, "est_R": e, "dif_rel_est": abs(est_py - e) / max(abs(e), 1e-12), "se_python": se_py, "se_R": s, "dif_rel_se": abs(se_py - s) / s})
tot = t1[(t1.variavel == "Total")].iloc[0]
for y, item in (("ia_total", "prev_total_any"), ("ia_grave", "prev_total_sev")):
    p = tot[f"{y}_pct"] / 100; lo, hi = tot[f"{y}_lo"] / 100, tot[f"{y}_hi"] / 100; se = (lg(hi) - lg(lo)) / (2 * Z) * p * (1 - p); add(item, p, se)
for b, c in ((0, "q1"), (4, "q5")):
    for y, sfx in (("ia_total", "y_any"), ("ia_grave", "y_sev")):
        r = t6[(t6.exposicao == "negra") & (t6.estratificado_por == "renda") & (t6.estrato == c) & (t6.desfecho == y)].iloc[0]; add(f"t6_negra_band{b}_{sfx}_logPR", np.log(r.rr_ajustado), (np.log(r.hi) - np.log(r.lo)) / (2 * Z))
r = at[(at.desfecho == "ia_total") & (at.variavel == "Negra") & (at.especificacao == "renda_e_demais")].iloc[0]; add("aten_negra_full_any_logPR", r.beta, (np.log(r.ic95_high) - np.log(r.ic95_low)) / (2 * Z))
for y, sfx in (("ia_total", "any"), ("ia_grave", "sev")):
    r = t3[(t3.desfecho == y) & (t3.termo == "negra:renda_q1")].iloc[0]; add(f"t3_negra_rq1_{sfx}_logPR", np.log(r.rr), (np.log(r.hi) - np.log(r.lo)) / (2 * Z))
for y, sfx in (("ia_total", "y_any"), ("ia_grave", "y_sev")):
    g = lambda q: s1[(s1.desfecho == y) & (s1.quantidade == q)].iloc[0]
    r = g("reri"); add(f"std_reri_{sfx}", r.padronizado_est, (r.padronizado_hi - r.padronizado_lo) / (2 * Z))
    r = g("ror"); add(f"std_log_ror_{sfx}", np.log(r.padronizado_est), (np.log(r.padronizado_hi) - np.log(r.padronizado_lo)) / (2 * Z))
    r = g("interacao_pp"); add(f"std_inter_pp_{sfx}", r.padronizado_est, (r.padronizado_hi - r.padronizado_lo) / (2 * Z))
    r = g("conjunta_pp"); add(f"std_joint_pp_{sfx}", r.padronizado_est, (r.padronizado_hi - r.padronizado_lo) / (2 * Z))
Rr = Rr.rename(index=lambda s: s.replace("std_log_ror", "std_log_ror").replace("std_reri_", "std_reri_"))
out = pd.DataFrame(rows)
out.to_csv(OUTD / "R11_comparacao_python_vs_R.csv", index=False, encoding="utf-8-sig"); print(out.to_string()); print("max dif rel est:", out.dif_rel_est.max(), "| max dif rel SE:", out.dif_rel_se.max())
