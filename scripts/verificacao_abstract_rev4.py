# -*- coding: utf-8 -*-
"""verificacao_abstract_rev4.py: confronta cada numero do RESUMO da rev4 (aba 'Abstract' de C_Traceability_table_rev4.xlsx) com valores obtidos por IMPLEMENTACAO INDEPENDENTE:
erros-padrao do pacote R `survey` (D4_validacao_R_survey.csv, R11_validacao_regressoes_R.csv) e o recalculo numpy da v1 (F_independent_verification.csv) para estimativas pontuais.
Mesmo arredondamento impresso. Saida: F_abstract_number_check_rev4.csv"""
import re, sys, json
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "MANUSCRITO_IJE_20260925"; RD = OUT / "rodada_D"; Z = 1.959964
T = pd.read_excel(OUT / "C_Traceability_table_rev4.xlsx", sheet_name="Abstract")
R4 = pd.read_csv(RD / "D4_validacao_R_survey.csv"); R4 = R4[R4.config == "C2"].set_index(["desfecho", "quantidade"])
R11 = pd.read_csv(RD / "R11_validacao_regressoes_R.csv").set_index("item")
F = pd.read_csv(OUT / "F_independent_verification.csv").set_index("item")
integ = json.loads((RD / "01_integridade_amostra.json").read_text(encoding="utf-8"))
lg = lambda p: np.log(p / (1 - p)); ex = lambda x: 1 / (1 + np.exp(-x))
def tokens(s):
    s = s.replace(" ", "").replace(" ", "")
    return [t.replace("−", "-").replace(",", "") for t in re.findall(r"−?\d[\d,]*\.?\d*", re.sub(r"95%", "", s))]
def fmt(v, dec): return f"{v:.{dec}f}"
def ratio_ci(est_log, se): return [np.exp(est_log), np.exp(est_log - Z * se), np.exp(est_log + Z * se)]
def lin_ci(e, se): return [e, e - Z * se, e + Z * se]
def prev_ci(p, se): s = se / (p * (1 - p)); return [p * 100, ex(lg(p) - Z * s) * 100, ex(lg(p) + Z * s) * 100]
rows = []
for r in T.itertuples():
    it = r.item; pr = str(r.printed); v = None; dec = 2; src = ""
    try:
        if it == "Total/Brasil: n": v = [integ["n_linhas_V2005_01"]]; dec = 0; src = "01_integridade_amostra.json (contagem no microdado bruto)"
        elif it.startswith("Total/Brasil: ia_total_pct"): v = prev_ci(R11.loc["prev_total_any", "est"], R11.loc["prev_total_any", "se"]); dec = 1; src = "R survey (svymean, replicas)"
        elif it.startswith("Total/Brasil: ia_grave_pct"): v = prev_ci(R11.loc["prev_total_sev", "est"], R11.loc["prev_total_sev", "se"]); dec = 1; src = "R survey (svymean, replicas)"
        elif "Race x Income" in it:
            y = "ia_grave" if "ia_grave" in it else "ia_total"; src = "R survey (withReplicates)"
            g = lambda q: R4.loc[(y, q)]
            if "rr11 (CI)" in it: v = ratio_ci(g("rr11").est_R, g("rr11").se_R)
            elif "reri (CI)" in it: v = lin_ci(g("reri").est_R, g("reri").se_R)
            elif "ror (CI)" in it: v = ratio_ci(g("ror").est_R, g("ror").se_R)
            elif "reri_esperado" in it: v = [g("reri_esperado").est_R]
            elif "interacao_pp" in it: v = lin_ci(g("interacao_pp").est_R, g("interacao_pp").se_R); dec = 1
            elif "joint difference" in it: v = [g("conjunta_pp").est_R]; dec = 1
        elif it.startswith("standardized sensitivity"):
            y = "y_sev" if "ia_grave" in it else "y_any"; v = lin_ci(R11.loc[f"std_reri_{y}" if f"std_reri_{y}" in R11.index else f"std_reri_{y}", "est"], R11.loc[f"std_reri_{y}", "se"]); src = "R (glm quasibinomial; replicas)"
        elif it.startswith("negra by renda=") and "rr_ajustado" in it:
            b = 0 if "renda=q1" in it else 4; y = "y_any" if "ia_total" in it else "y_sev"; v = ratio_ci(R11.loc[f"t6_negra_band{b}_{y}_logPR", "est"], R11.loc[f"t6_negra_band{b}_{y}_logPR", "se"]); src = "R survey (svyglm quasipoisson; replicas)"
        elif it.startswith("negra by renda=") and "dif_pp" in it:
            band = it.split("renda=")[1].split(" /")[0]; d_ = it.split("/ ")[1].split(":")[0]; v = [float(F.loc[f"crude difference Black - non-Black, income band {band}, {d_} (pp)", "independent"])]; dec = 1; src = "numpy independente (v1; estimativa pontual)"
        elif it.startswith("MAIHDA") and "pcv" in it:
            d_ = it.split()[1].rstrip(":"); v = [float(F.loc[f"MAIHDA PCV from sigma2 ({d_}) (%)", "independent"])]; dec = 1; src = "aritmetica dos sigma2 (independente)"
        if v is None: rows.append({"abstract_item": it, "printed": pr, "independent_at_printed_rounding": "", "status": "NOT MAPPED", "independent_source": ""}); continue
        got = tokens(pr)[:len(v)]; want = [fmt(x, dec).replace("−", "-") for x in v]
        ok = got == want
        rows.append({"abstract_item": it, "printed": pr, "independent_at_printed_rounding": " | ".join(fmt(x, dec).replace("-", "−") for x in v), "status": "MATCH" if ok else "MISMATCH", "independent_source": src})
    except KeyError as e:
        rows.append({"abstract_item": it, "printed": pr, "independent_at_printed_rounding": "", "status": f"NO INDEPENDENT VALUE ({e})", "independent_source": ""})
res = pd.DataFrame(rows); res.to_csv(OUT / "F_abstract_number_check_rev4.csv", index=False, encoding="utf-8-sig")
print(res.status.value_counts().to_string()); print(res[res.status != "MATCH"].to_string())
