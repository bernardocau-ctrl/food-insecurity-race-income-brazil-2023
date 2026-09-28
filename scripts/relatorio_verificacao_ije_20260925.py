# -*- coding: utf-8 -*-
"""Confronta cada numero do RESUMO (aba 'Abstract' da tabela de rastreabilidade) com o recalculo independente (F_independent_verification.csv),
no MESMO arredondamento impresso. Saida: F_abstract_number_check_rev3.csv"""
import re, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from ms_numeros_20260925 import f1, f2, ci
OUT = Path(__file__).resolve().parent.parent / "MANUSCRITO_IJE_20260925"
F = pd.read_csv(OUT / "F_independent_verification.csv").set_index("item")
T = pd.read_excel(OUT / "C_Traceability_table_rev3.xlsx", sheet_name="Abstract")
ind = lambda k: float(F.loc[k, "independent"])
PAR = {"Race x Income": "Race x Income"}
def tokens(s):
    s = s.replace(" ", "")
    return [t.replace("−", "-").replace(",", "") for t in re.findall(r"−?\d[\d,]*\.?\d*", re.sub(r"95%", "", s))]
def fmt(v, dec): return (f"{v:.{dec}f}").replace("-", "−")
rows = []
for r in T.itertuples():
    it = r.item; pr = str(r.printed); est = None
    def pack(vals, decs, kind="ci"):
        return vals, decs
    try:
        if it.startswith("Total/Brasil: ia_") and "_pct" in it:
            d = "ia_total" if "ia_total" in it else "ia_grave"; base = f"overall weighted prevalence {d}"
            v = [ind(base + " (%)"), ind(base + " 95% CI lower (%)"), ind(base + " 95% CI upper (%)")]; dec = 1
        elif it.startswith("Total/Brasil: n"):
            v = [ind("analytic sample size (households)")]; dec = 0
        elif "Race x Income" in it and "/ ia_grave: rr11" in it:
            b = "Race x Income/ia_grave: PR rr11 95% CI"; v = [ind("Race x Income/ia_grave: PR (both)"), ind(b + " lower"), ind(b + " upper")]; dec = 2
        elif "Race x Income" in it and "reri (CI)" in it:
            d = "ia_grave" if "ia_grave" in it else "ia_total"; b = f"Race x Income/{d}: RERI 95% CI"
            v = [ind(f"Race x Income/{d}: RERI"), ind(b + " lower (independent linearisation)"), ind(b + " upper (independent linearisation)")]; dec = 2
        elif "Race x Income" in it and "ror (CI)" in it:
            d = "ia_grave" if "ia_grave" in it else "ia_total"; b = f"Race x Income/{d}: ratio of PRs 95% CI"; v = [ind(f"Race x Income/{d}: ratio of PRs"), ind(b + " lower"), ind(b + " upper")]; dec = 2
        elif "Race x Income" in it and "reri_esperado" in it:
            d = "ia_grave" if "ia_grave" in it else "ia_total"; v = [ind(f"Race x Income/{d}: expected RERI")]; dec = 2
        elif "Race x Income" in it and "interaction contrast" in it:
            d = "ia_grave" if "ia_grave" in it else "ia_total"; v = [ind(f"Race x Income/{d}: interaction contrast (pp)")]; dec = 1
        elif "Race x Income" in it and "joint difference (p11-p00)" in it:
            d = "ia_grave" if "ia_grave" in it else "ia_total"; v = [ind(f"Race x Income/{d}: joint difference (pp)")]; dec = 1
        elif it.startswith("negra by renda=") and "rr_ajustado (CI)" in it:
            band = it.split("renda=")[1].split(" /")[0]; d = it.split("/ ")[1].split(":")[0]
            tag = f"adjusted PR Black, income band {band}, {d}"; v = [ind(tag), ind(tag + " CI lower"), ind(tag + " CI upper")]; dec = 2
        elif it.startswith("negra by renda=") and ": dif_pp" in it:
            band = it.split("renda=")[1].split(" /")[0]; d = it.split("/ ")[1].split(":")[0]
            v = [ind(f"crude difference Black - non-Black, income band {band}, {d} (pp)")]; dec = 1
        elif it.startswith("MAIHDA") and "pcv" in it:
            d = it.split()[1].rstrip(":"); v = [ind(f"MAIHDA PCV from sigma2 ({d}) (%)")]; dec = 1
        else:
            rows.append({"abstract_item": it, "printed": pr, "independent_at_printed_rounding": "", "status": "NOT MAPPED", "source_in_C": r.source}); continue
        indp = " | ".join(fmt(x, dec) for x in v)
        ok = tokens(pr)[:len(v)] == [fmt(x, dec).replace("−", "-") for x in v]
        rows.append({"abstract_item": it, "printed": pr, "independent_at_printed_rounding": indp, "status": "MATCH" if ok else "MISMATCH", "source_in_C": r.source})
    except KeyError as e:
        rows.append({"abstract_item": it, "printed": pr, "independent_at_printed_rounding": "", "status": f"NO INDEPENDENT VALUE ({e})", "source_in_C": r.source})
res = pd.DataFrame(rows); res.to_csv(OUT / "F_abstract_number_check_rev3.csv", index=False, encoding="utf-8-sig")
print(res.status.value_counts().to_string()); print(res[res.status != "MATCH"].to_string())
