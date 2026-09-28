# -*- coding: utf-8 -*-
"""
coerencia_ije_20260925.py

Controle de coerencia ANTES de redigir o manuscrito IJE. NAO estima nada novo:
so' verifica identidades e concordancia entre estimativas que ja existem nos
CSVs de dados/ e dados/v2_20260925/ (mesmos arquivos do manuscrito SSM).

Saida: MANUSCRITO_IJE_20260925/C_coherence_checks.csv (+ impressao)
"""
import re
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
D = BASE / "dados" / "v2_20260925"; D16 = BASE / "dados"
SAN = BASE.parent.parent            # .../san
OUT = BASE / "MANUSCRITO_IJE_20260925"; OUT.mkdir(exist_ok=True)

t2 = pd.read_csv(D / "t2_pares.csv"); t3 = pd.read_csv(D / "t3_conjunto.csv"); t6 = pd.read_csv(D / "t6_estratificado.csv")
old1 = pd.read_csv(D16 / "interseccional_2023.csv"); old2 = pd.read_csv(D16 / "interseccional_2023_parte2.csv"); old3 = pd.read_csv(D16 / "interseccional_2023_parte3.csv")

rows = []
def add(check, item, value, expected, status, note=""):
    rows.append({"check": check, "item": item, "value": value, "expected_or_comparator": expected, "status": status, "note": note})

pairs = {"Race x Sex": "sex", "Race x Education": "edu", "Race x Income": "inc", "Race x Residence": "res"}
old_map = {("sex", "ia_total"): old1.iloc[0], ("sex", "ia_grave"): old1.iloc[1], ("edu", "ia_total"): old1.iloc[2], ("edu", "ia_grave"): old1.iloc[3],
           ("inc", "ia_total"): old1.iloc[4], ("inc", "ia_grave"): old1.iloc[5], ("res", "ia_total"): old3.iloc[0], ("res", "ia_grave"): old3.iloc[1]}

for r in t2.itertuples():
    k = [v for kk, v in pairs.items() if r.par.startswith(kk)][0]
    tag = f"{k}/{r.desfecho}"
    o = old_map[(k, r.desfecho)]
    # A. prevalencias das 4 celulas: v2 (t2) vs rodada de 16/09 (arquivos originais)
    dif = max(abs(r.p00 - o.prev_00), abs(r.p10 - o.prev_10), abs(r.p01 - o.prev_01), abs(r.p11 - o.prev_11))
    add("A. cell prevalences v2 vs 16/09 files", tag, f"max|diff|={dif:.2e} pp", "<1e-6", "PASS" if dif < 1e-6 else "FAIL")
    # B. PR == razao das prevalencias ponderadas (modelo Poisson saturado)
    d_pr = max(abs(r.rr10 - r.p10 / r.p00), abs(r.rr01 - r.p01 / r.p00), abs(r.rr11 - r.p11 / r.p00))
    add("B. PR = ratio of weighted cell prevalences", tag, f"max|diff|={d_pr:.2e}", "<1e-4", "PASS" if d_pr < 1e-4 else "FAIL")
    # C. RERI = RR11-RR10-RR01+1  e  RERI = contraste de interacao em pp / prevalencia da referencia
    reri_def = r.rr11 - r.rr10 - r.rr01 + 1
    ic_pp = r.p11 - r.p10 - r.p01 + r.p00
    add("C1. RERI = PR11-PR10-PR01+1", tag, f"reported={r.reri:.4f}; from PRs={reri_def:.4f}", "equal", "PASS" if abs(r.reri - reri_def) < 1e-6 else "FAIL")
    add("C2. RERI x p00 = interaction contrast (pp)", tag, f"RERI*p00={r.reri * r.p00:.4f} pp; contrast={ic_pp:.4f} pp", "equal (identity)", "PASS" if abs(r.reri * r.p00 - ic_pp) < 1e-3 else "FAIL",
        "Identity for the saturated 2x2 model: interaction contrast in absolute units = RERI x reference prevalence.")
    # D. decomposicao
    joint = r.p11 - r.p00; a = r.p10 - r.p00; b = r.p01 - r.p00
    add("D. joint = race + other + interaction (pp)", tag, f"{joint:.4f} = {a:.4f} + {b:.4f} + {ic_pp:.4f} -> sum {a + b + ic_pp:.4f}", "equal", "PASS" if abs(joint - (a + b + ic_pp)) < 1e-6 else "FAIL",
        f"interaction share = {ic_pp / joint * 100:.2f}%")
    # E. expected RERI sob multiplicatividade
    add("E. expected RERI = (PR10-1)(PR01-1)", tag, f"reported={r.reri_esperado_nulo_mult:.4f}; recomputed={(r.rr10 - 1) * (r.rr01 - 1):.4f}", "equal",
        "PASS" if abs(r.reri_esperado_nulo_mult - (r.rr10 - 1) * (r.rr01 - 1)) < 1e-6 else "FAIL")
    # F. IC delta vs bootstrap (arquivos de 16/09)
    if not (k in ("sex", "edu", "inc") and r.desfecho == "ia_grave"):
        blo, bhi = o.reri_ic95_low, o.reri_ic95_high
    else:
        src = old2[old2.parte == "a_nacional_grave"].reset_index(drop=True)
        i = {"sex": 0, "edu": 1, "inc": 2}[k]
        blo, bhi = src.loc[i, "reri_ic95_low"], src.loc[i, "reri_ic95_high"]
    dd = max(abs(r.reri_lo_delta - blo), abs(r.reri_hi_delta - bhi))
    add("F. RERI 95% CI: delta vs cluster bootstrap", tag, f"delta=[{r.reri_lo_delta:.3f},{r.reri_hi_delta:.3f}]; boot=[{blo:.3f},{bhi:.3f}]; max|diff|={dd:.3f}", "close (<0.07)", "PASS" if dd < 0.07 else "NOTE")

# G. o modelo das 4 celulas e' BRUTO (sem covariaveis)? -> ler a formula no script
src_txt = (SAN / "analise_consolidada_artigo3_20260925.py").read_text(encoding="utf-8")
m = re.search(r'fit_poisson\(sub, f"\{d\} ~ c10 \+ c01 \+ c11"', src_txt)
add("G. 2x2 joint-category model has no covariates", "analise_consolidada...py (T2)", "formula: {d} ~ c10 + c01 + c11 (survey-weighted, cluster-robust)", "crude", "CONFIRMED CRUDE" if m else "CHECK",
    "RERI, PRs of joint categories, ratio of PRs and the decomposition are UNADJUSTED for sex, education, residence, region, age. Only the stratum-specific PRs and the mutually adjusted model are adjusted.")
m2 = re.search(r'prev_ci_full\(s2\[s2\[expos\] == 1\], d\)', src_txt)
add("H. stratum-specific absolute gap is crude, PR adjusted", "t6 (analise_consolidada T6)", "dif_pp = prevalence(exposed) - prevalence(unexposed) within stratum, no covariates; rr_ajustado = adjusted Poisson", "mixed", "CONFIRMED MIXED" if m2 else "CHECK",
    "Relative gap (adjusted PR) and absolute gap (crude difference) in Fig. 2 are not from the same model. Adjusted prevalence difference is NOT available -> VERIFICAR NO CODIGO/DADOS if wanted.")
d_gap = (t6.prev_exposto - t6.prev_nao_exposto - t6.dif_pp).abs().max()
add("H2. dif_pp = prev_exposto - prev_nao_exposto", "t6 all rows", f"max|diff|={d_gap:.2e}", "<1e-6", "PASS" if d_gap < 1e-6 else "FAIL")

# I. RoR bruto (2x2) x produto do modelo mutuamente ajustado (t3) - so' comparar, nao substituir
for k, term in [("inc", "negra:renda_q1"), ("edu", "negra:sem_fund")]:
    for d in ["ia_total", "ia_grave"]:
        rr_ = t2[t2.par.str.startswith({"inc": "Race x Income", "edu": "Race x Education"}[k]) & (t2.desfecho == d)].iloc[0]
        j = t3[(t3.termo == term) & (t3.desfecho == d)].iloc[0]
        add("I. crude 2x2 ratio of PRs vs mutually adjusted product term", f"{k}/{d}", f"crude={rr_.ror:.3f}; mutually adjusted={j.rr:.3f}", "same direction", "NOTE",
            "Different models (crude vs adjusted for sex, residence and the other three race products). Do not present as the same estimate.")

# J. codigo 9 (ignorado) em 'nao negra'? nao verificavel a partir dos CSVs
add("J. 'non-Black' composition", "V2010 coding in preparar()", "negra = V2010 in {2,4}; non-Black = everything else, including code 9 (unrecorded) if present", "cannot verify from CSVs",
    "VERIFICAR NO CODIGO/DADOS", "The manuscript must not equate non-Black with white. Number of code-9 records in the analytic sample is not in the derived files.")

res = pd.DataFrame(rows)
res.to_csv(OUT / "C_coherence_checks.csv", index=False, encoding="utf-8-sig")
print(res.groupby("status").size().to_string())
print(res[res.status.isin(["FAIL", "CHECK"])].to_string())
inc = t2[t2.par.str.startswith("Race x Income")]
for r in inc.itertuples():
    print(r.desfecho, "RERI=%.4f  p00=%.4f  RERI*p00=%.4f pp  contrast=%.4f pp  joint=%.4f pp" % (r.reri, r.p00, r.reri * r.p00, r.p11 - r.p10 - r.p01 + r.p00, r.p11 - r.p00))
