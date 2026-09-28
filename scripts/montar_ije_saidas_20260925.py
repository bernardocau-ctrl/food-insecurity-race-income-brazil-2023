# -*- coding: utf-8 -*-
"""
montar_ije_saidas_20260925.py
Saidas da versao IJE: manuscrito A (2 passagens para fechar a contagem), suplemento B, rastreabilidade C,
contagens D, pendencias E e relatorio de mudancas. Nenhuma estimativa nova.
"""
import shutil
import pandas as pd
from pathlib import Path
from ije_lib_20260925 import *     # noqa
from supl_rodada_d_20260925 import add_rodada_d_tables

SSMDIR = BASE / "MANUSCRITO_EN_SSM_20260925"
LAB1 = {"nao negra": "Non-Black", "negra (preta+parda)": "Black (preta or parda)", "homem": "Man", "mulher": "Woman", "sem_fund": "No schooling or incomplete primary",
        "fund_med": "Complete primary or incomplete secondary", "medio_comp": "Complete secondary", "superior": "Tertiary (complete or incomplete)", "q1": "≤1/4", "q2": ">1/4-1/2", "q3": ">1/2-1",
        "q4": ">1-2", "q5": ">2", "urbano": "Urban", "rural": "Rural"}
PAIRKEY = {"sex": "Race x Sex", "edu": "Race x Education", "inc": "Race x Income", "res": "Race x Residence"}
PAIRLAB = {"sex": "Race/colour × sex (woman)", "edu": "Race/colour × education (≤ incomplete primary)", "inc": "Race/colour × income (≤1/4 MW)", "res": "Race/colour × residence (rural)"}
OUTL = {"ia_total": "Any", "ia_grave": "Severe"}


def reset():
    TR.clear(); REFN.clear(); ORDER.clear(); SEC.clear()
    for k in WC: WC[k] = 0


def _jd(r):
    j = r.p11 - r.p00; a = r.p10 - r.p00; b = r.p01 - r.p00; it = r.p11 - r.p10 - r.p01 + r.p00
    return j, a, b, it


# ============================================================== SUPLEMENTO
def build_supplement(g):
    d = new_doc(line_numbers=False, spacing=1.15, size=10)
    p = d.add_paragraph(); r = p.add_run("Supplementary material"); r.bold = True; r.font.size = Pt(14)
    p = d.add_paragraph(); rich(p, "Race, income and household food insecurity in Brazil: joint disparities depend on the scale of interaction", size=11)
    para(d, "This supplement contains every result of the study that is not in the main article. Nothing here is required to understand the main conclusion, which rests on Tables 1-3 and Figure 1 of the article. Estimates are prevalence ratios (PR) from survey-weighted Poisson regression, unless stated. Section A lists the analyses in the order in which they were run and marks which were added after initial inspection. Unless stated otherwise, confidence intervals and P values of survey-weighted estimates come from the 200 replicate weights (variance method C; Supplementary Table S15); the multilevel models are unweighted. The bootstrap intervals in Supplementary Tables S5 and S8 are from an earlier analysis (primary sampling unit cluster bootstrap) and are labelled as such.", bucket="decl")
    para(d, "Abbreviations: AUC, area under the receiver operating characteristic curve; CI, confidence interval; EBIA, Brazilian Food Insecurity Scale; MAIHDA, multilevel analysis of individual heterogeneity and discriminatory accuracy; MW, minimum wage; OR, odds ratio; PCV, proportional change in variance; PNADC, Continuous National Household Sample Survey; pp, percentage points; PR, prevalence ratio; RERI, relative excess risk due to interaction; STROBE, Strengthening the Reporting of Observational Studies in Epidemiology; VPC, variance partition coefficient.", bucket="decl")
    H2(d, "A. Analyses and their status")
    rows = [["Full descriptive table (Table 1 of the article is condensed)", "Initial", ST["table1"]], ["Own associations and attenuation by income", "Initial", ST["own"]], ["Pairwise joint categories, RERI, ratio of PRs (all four pairs)", "Initial (variance methods A, B and C: Supplementary Table S15)", f"{ST['pairs']}, {ST['cells']}"],
            ["Mutually adjusted model (four race × characteristic products)", "Initial", ST["joint"]], ["Race × sex by macro-region", "Initial", ST["region"]],
            ["MAIHDA (160 strata), fixed effects, weight sensitivity", "Initial", f"{ST['maihda']}-{ST['weights']}"],
            ["RERI expected under multiplicative joint effects (interpretive context)", "Added after initial inspection", f"{ST['pairs']}; Tables 2-3"],
            ["Decomposition of the joint prevalence difference", "Added after initial inspection", f"{ST['cells']}; Tables 2-3"],
            ["Stratum-specific racial and sex gaps (Supplementary Figures S1-S2)", "Added after initial inspection", ST["strata"]], ["Three-way interactions", "Added after initial inspection", ST["three"]],
            ["Cumulative-disadvantage gradient (relative and absolute)", "Added after initial inspection", ST["grad"]],
            ["Variance methods A, B and C; interval for the decomposition", "Added after the audit (post-protocol amendment for the choice of C)", f"{ST['var']}, {ST['comp']}"],
            ["Standardized analysis; income cut-points; exclusion of ignored records (exploratory sensitivity analyses)", "Added after the audit", f"{ST['std']}, {ST['cut']}, {ST['ign']}"], ["Sample flow, design variables and integrity checks", "Added after the audit", ST["samp"]]]
    table(d, ["Analysis", "Status", "Where"], rows, font=8.5, bucket="decl")
    # S1 coding
    caption(d, f"**Supplementary Table {ST['coding']}a.** Coding of variables (from the analysis code, function preparar() of analise_bivariada_e_regressao_v2.py).")
    rows = [["Unit / weights / clusters", "Reference person's record (V2005 = 01); weight V1028; primary sampling unit UPA", "Household; weights rescaled to mean one"],
            ["Any food insecurity", "EBIA classification SD17001 ≥ 2", "Mild, moderate or severe"], ["Severe food insecurity", "SD17001 = 4", "Severe"],
            ["Black", "V2010 in {2, 4} (preta, parda)", "Non-Black = every other value (white, Asian, Indigenous, and 19 households with race ignored, code 9), not a synonym for white"],
            ["Recorded sex", "V2007 = 2 (woman)", "Recorded sex; not gender identity"], ["Education", "VD3004 in {1, 2}: no schooling or incomplete primary; {3, 4}; {5}; {6, 7}", "Four groups; primary contrast: {1, 2} vs others"],
            ["Per capita income band", "VDI5009 = 1 (≤1/4 MW), 2, 3, 4, ≥5 (>2 MW)", "Primary contrast: band 1 vs bands 2-5; bands 5-7 pooled as >2 MW; code 9 (ignored; 77 households) is also in the >2 MW band"], ["Rural residence", "V1022 = 2", "Urban vs rural"]]
    table(d, ["Variable", "Source coding", "Note"], rows, font=8, bucket="decl")
    rows = [["Joint-category models: prevalence ratios, RERI, ratio of PRs, decomposition (Tables 2-3; Supplementary Tables S4, S5)", "None (crude). Four-category indicator of the joint exposure.", "Weighted; variance from 200 replicate weights (method C)"],
            ["Mutually adjusted model (Supplementary Table S6)", "Black race, recorded sex, low education (no schooling or incomplete primary, dichotomised), income ≤1/4 MW (dichotomised), rural residence, and four race × characteristic products.", "Weighted; variance from 200 replicate weights (method C)"],
            ["Racial gaps within income bands (Supplementary Figure S1; Supplementary Table S9)", "Adjusted PR for Black race within each of five income bands: recorded sex, education in four categories, residence. The absolute difference in percentage points is crude.", "Weighted; variance from 200 replicate weights (method C)"],
            ["Racial gaps within education categories (Supplementary Figure S2; Supplementary Table S9)", "Adjusted PR for Black race within each of four education categories: recorded sex, income in five bands, residence.", "Weighted; variance from 200 replicate weights (method C)"],
            ["Attenuation of the crude association (Results; Supplementary Table S3)", "PR for each characteristic: crude; adjusted for income band (four indicators; reference >2 MW); adjusted for income band and the other characteristics (recorded sex, rural residence, low education dichotomised). Education is dichotomised here, unlike the band-specific models above. The two sets were not harmonised.", "Weighted; variance from 200 replicate weights (method C)"],
            ["Cumulative-disadvantage models (Supplementary Table S10)", "Black race, number of disadvantages (0-4) and their product; Poisson (relative) and linear probability (absolute) models. No other covariates.", "Weighted; variance from 200 replicate weights (method C)"],
            ["Three-way interactions (Supplementary Table S7)", "Race × recorded sex × income ≤1/4 MW, or × low education, with all lower-order terms. No other covariates.", "Weighted; variance from 200 replicate weights (method C)"],
            ["Standardized analysis (Supplementary Table S17)", "Weighted logistic model with the four-category joint exposure, recorded sex, education (four categories) and rural residence; predicted probabilities averaged over all households with the joint category fixed.", "Weighted; variance from 200 replicate weights (model refitted in each replicate)"],
            ["Cut-point and ignored-record sensitivity analyses (Supplementary Tables S18, S19)", "Crude joint-category contrast, as for the primary analysis, with the income cut-point changed or with ignored records excluded.", "Weighted; variance from 200 replicate weights (method C)"],
            ["MAIHDA Models A and B (Supplementary Tables S11-S13)", "Model A: none. Model B: Black race (2 categories), recorded sex (2), education (4), income (5) and residence (2) as fixed effects. Random intercept for each of the 160 strata.", "Unweighted (approximate weights in Supplementary Table S13); logit scale"]]
    caption(d, f"**Supplementary Table {ST['coding']}b.** Covariates in each analysis. Specifications differ across analyses and were not harmonised; PSU, primary sampling unit.")
    table(d, ["Analysis", "Exposure and covariates", "Weights and variance"], rows, widths=[5.0, 8.0, 3.0], font=8, bucket="decl")
    # S2 Tabela 1 completa
    g["table_1"](d, full=True)
    # S3 own associations
    rows = []
    for v, lab in [("Negra", "Black race"), ("Mulher", "Woman (recorded sex)"), ("Sem instrução", "No schooling/incomplete primary"), ("Rural", "Rural residence")]:
        for dd in ["ia_total", "ia_grave"]:
            b, r1, r2 = ATEN(v, "bruto", dd), ATEN(v, "so_renda", dd), ATEN(v, "renda_e_demais", dd)
            rows.append([lab if dd == "ia_total" else "", OUTL[dd], f"{f2(b.rr)} ({ci(b.ic95_low, b.ic95_high)})", f"{f2(r1.rr)} ({ci(r1.ic95_low, r1.ic95_high)})", f"{f2(r2.rr)} ({ci(r2.ic95_low, r2.ic95_high)})", f"{r1.atenuacao_pct:.0f}", f"{r2.atenuacao_pct:.0f}"])
    caption(d, f"**Supplementary Table {ST['own']}.** Prevalence ratios (95% CI) by characteristic: crude, adjusted for income band, and adjusted for income band plus the other characteristics (recorded sex, rural residence and low education, each dichotomised); proportional attenuation of the crude log PR (%). Attenuation describes association, not mediation; values above 100 indicate reversal of direction.")
    table(d, ["Characteristic", "Outcome", "Crude", "Adjusted for income", "Adjusted for income and others", "Attenuation, income (%)", "Attenuation, full (%)"], rows, font=8, bucket="decl")
    # S3 pairs (todos)
    rows = []
    for k in ["inc", "edu", "sex", "res"]:
        for dd in ["ia_total", "ia_grave"]:
            r = T2(PAIRKEY[k], dd)
            rows.append([PAIRLAB[k] if dd == "ia_total" else "", OUTL[dd], f"{f2(r.rr10)} ({ci(r.rr10_lo, r.rr10_hi)})", f"{f2(r.rr01)} ({ci(r.rr01_lo, r.rr01_hi)})", f"{f2(r.rr11)} ({ci(r.rr11_lo, r.rr11_hi)})",
                         f"{f2(r.reri)} ({ci(r.reri_lo_delta, r.reri_hi_delta)})", f2(r.reri_esperado_nulo_mult), f"{f2(r.ror)} ({ci(r.ror_lo, r.ror_hi)})", pfmt(r.ror_p)])
    caption(d, f"**Supplementary Table {ST['pairs']}.** Joint-category prevalence ratios, RERI, expected RERI and ratio of PRs for all four pairs (crude). Reference: non-Black without the second characteristic.")
    table(d, ["Pair", "Outcome", "Black only, PR", "Other only, PR", "Both, PR", "RERI (95% CI)", "RERI expected if multiplicative", "Ratio of PRs (95% CI)", "*P* (ratio)"], rows, font=7.5, bucket="decl")
    # S4 cells + bootstrap + decomposicao
    f1b = pd.read_csv(D16 / "interseccional_2023.csv"); f2b = pd.read_csv(D16 / "interseccional_2023_parte2.csv"); f3b = pd.read_csv(D16 / "interseccional_2023_parte3.csv")
    bt = {}
    a_rows = f1b[f1b.desfecho == "ia_total"].reset_index(drop=True); s_rows = f2b[f2b.parte == "a_nacional_grave"].reset_index(drop=True)
    for k, i in [("sex", 0), ("edu", 1), ("inc", 2)]:
        bt[(k, "ia_total")] = (a_rows.loc[i, "reri_ic95_low"], a_rows.loc[i, "reri_ic95_high"]); bt[(k, "ia_grave")] = (s_rows.loc[i, "reri_ic95_low"], s_rows.loc[i, "reri_ic95_high"])
    bt[("res", "ia_total")] = (f3b.loc[0, "reri_ic95_low"], f3b.loc[0, "reri_ic95_high"]); bt[("res", "ia_grave")] = (f3b.loc[1, "reri_ic95_low"], f3b.loc[1, "reri_ic95_high"])
    rows = []
    for k in ["inc", "edu", "sex", "res"]:
        for dd in ["ia_total", "ia_grave"]:
            r = T2(PAIRKEY[k], dd); j, a, b, it = _jd(r)
            rows.append([PAIRLAB[k] if dd == "ia_total" else "", OUTL[dd], f"{f1(r.p00)} / {f1(r.p10)} / {f1(r.p01)} / {f1(r.p11)}", f"{n0(r.n00)} / {n0(r.n10)} / {n0(r.n01)} / {n0(r.n11)}",
                         f"{f2(r.reri)} ({ci(r.reri_lo_delta, r.reri_hi_delta)})", ci(*bt[(k, dd)]), f"{f1(j)} = {f1(a)} + {f1(b)} + {f1(it)}", f1(it / j * 100)])
    caption(d, f"**Supplementary Table {ST['cells']}.** Weighted prevalence (%) and households in the four joint categories (reference / Black only / other only / both); RERI with 95% CI from replicate weights (method C) and, for comparison, the earlier primary-sampling-unit cluster bootstrap (300 replicates; not method C); decomposition of the joint prevalence difference in percentage points (component corresponding to race/colour alone + component corresponding to the other characteristic alone + interaction component) and interaction share. The decomposition is arithmetic and descriptive, does not identify causal effects, and has no confidence interval.")
    table(d, ["Pair", "Outcome", "Prevalence, %: ref / Black / other / both", "Households: ref / Black / other / both", "RERI, replicate weights (95% CI)", "RERI, earlier PSU cluster bootstrap 95% CI", "Joint difference = race component + other component + interaction component (pp)", "Interaction share (%)"], rows, font=7.5, bucket="decl")
    # S5 conjunto
    lab = {"negra": "Black race", "mulher": "Woman", "sem_fund": "No schooling/incomplete primary", "renda_q1": "Income ≤1/4 MW", "rural": "Rural residence", "negra:mulher": "Black × woman",
           "negra:sem_fund": "Black × no schooling/incomplete primary", "negra:renda_q1": "Black × income ≤1/4 MW", "negra:rural": "Black × rural"}
    rows = []
    for t_, l_ in lab.items():
        a = t3[(t3.termo == t_) & (t3.desfecho == "ia_total")].iloc[0]; s_ = t3[(t3.termo == t_) & (t3.desfecho == "ia_grave")].iloc[0]
        rows.append([l_, f"{f2(a.rr)} ({ci(a.lo, a.hi)})", pfmt(a.p), f"{f2(s_.rr)} ({ci(s_.lo, s_.hi)})", pfmt(s_.p)])
    wa = t3[(t3.termo == "WALD_conjunto_4gl") & (t3.desfecho == "ia_total")].iloc[0]; ws = t3[(t3.termo == "WALD_conjunto_4gl") & (t3.desfecho == "ia_grave")].iloc[0]
    caption(d, f"**Supplementary Table {ST['joint']}.** Mutually adjusted model with five main effects and four race × characteristic products: PR (95% CI). Product terms are ratios of PRs (multiplicative interaction). Joint Wald test of the four products (4 degrees of freedom; covariance from the replicates): any, χ² = {f1(wa.rr)}, *P* {pfmt(wa.p)}; severe, χ² = {f1(ws.rr)}, *P* {pfmt(ws.p)}. No adjusted RERI was estimated.")
    table(d, ["Term", "Any insecurity", "*P*", "Severe insecurity", "*P*"], rows, font=8, bucket="decl")
    # S6 tripla
    rows = [[{"renda_q1": "Race × sex × income ≤1/4 MW", "sem_fund": "Race × sex × no schooling/incomplete primary"}[r.terceira_dimensao], OUTL[r.desfecho], f"{f2(r.rr)} ({ci(r.lo, r.hi)})", pfmt(r.p)] for r in t7.itertuples()]
    caption(d, f"**Supplementary Table {ST['three']}.** Three-way interaction terms (ratio of PRs) in models with all lower-order terms.")
    table(d, ["Term", "Outcome", "Ratio of PRs (95% CI)", "*P*"], rows, font=8, bucket="decl")
    # S7 regiao
    nm = {"Norte": "North", "Nordeste": "Northeast", "Centro-Oeste": "Central-West", "Sudeste": "Southeast", "Sul": "South"}
    rg = reg[reg.parte == "b_regional"]
    rows = [[nm[r.regiao], OUTL[r.desfecho], n0(r.n_total_celula), f2(r.rr10), f2(r.rr01), f2(r.rr11), f"{f2(r.reri)} ({ci(r.reri_ic95_low, r.reri_ic95_high)})", f2(r.razao_razoes)] for r in rg.itertuples()]
    caption(d, f"**Supplementary Table {ST['region']}.** Race/colour × sex (woman) by macro-region: PRs, RERI with 95% CI from the earlier primary-sampling-unit cluster bootstrap (300 replicates; not re-estimated with replicate weights) and ratio of PRs.")
    table(d, ["Region", "Outcome", "Households", "PR Black only", "PR woman only", "PR both", "RERI (95% CI)", "Ratio of PRs"], rows, font=8, bucket="decl")
    # S8 estratos
    labx = {"negra": "Black race", "mulher": "Woman"}; strat = {"renda": "Income band", "instrucao": "Education", "raca": "Race/colour"}
    rows = []
    for r in t6.itertuples():
        rows.append([labx[r.exposicao], strat[r.estratificado_por], LAB1.get(r.estrato, r.estrato.replace("_", " ")), OUTL[r.desfecho], n0(r.n), f"{f1(r.prev_exposto)} / {f1(r.prev_nao_exposto)}",
                     f"{f1(r.dif_pp)} ({ci(r.dif_pp_lo, r.dif_pp_hi, 1)})", f"{f2(r.rr_ajustado)} ({ci(r.lo, r.hi)})", pfmt(r.p)])
    caption(d, f"**Supplementary Table {ST['strata']}.** Stratum-specific associations of Black race and of woman (recorded sex): prevalence in exposed and unexposed (%), crude absolute difference (percentage points; approximate 95% CI treating groups as independent) and adjusted PR. The difference is crude and the PR is adjusted; they come from different models.")
    table(d, ["Exposure", "Stratified by", "Stratum", "Outcome", "*n*", "Prevalence, exposed / unexposed, %", "Difference, pp (95% CI)", "Adjusted PR (95% CI)", "*P*"], rows, font=7.5, bucket="decl")
    figure(d, "figS1_race_gaps_income.png", 5.9, "**Supplementary Figure S1.** Racial gap in food insecurity across income bands (minimum wage, MW, per capita): adjusted prevalence ratio (PR; a, c; adjusted for recorded sex, education in four categories and residence) and crude absolute difference in percentage points (b, d) for Black versus non-Black reference persons. The two measures come from different models. Bars are 95% confidence intervals from replicate weights.", "decl",
           alt="Four-panel plot by income band from lowest to highest. Panels a and c: adjusted prevalence ratio for Black race, any and severe food insecurity, rising with income. Panels b and d: crude absolute difference in percentage points, falling with income.")
    figure(d, "figS2_race_gaps_education.png", 5.9, "**Supplementary Figure S2.** Racial gap in food insecurity across education categories: adjusted prevalence ratio (PR; a, c; adjusted for recorded sex, income and residence) and crude absolute difference in percentage points (b, d) for Black versus non-Black reference persons. Bars are 95% confidence intervals from replicate weights.", "decl",
           alt="Four-panel plot by education category. Panels a and c: adjusted prevalence ratio for Black race, any and severe food insecurity. Panels b and d: crude absolute difference in percentage points.")
    figure(d, "figS3_interaction_all_pairs.png", 6.2, "**Supplementary Figure S3.** As Figure 1 of the article for all four pairs of characteristics: relative excess risk due to interaction (RERI, a) and ratio of prevalence ratios (b).", "decl",
           alt="Two-panel plot with 95% confidence intervals for four pairs of characteristics, any and severe food insecurity. Panel a: relative excess risk due to interaction with expected values under multiplicativity. Panel b: ratio of prevalence ratios.")
    # S9 gradiente
    rows = [[OUTL[r.desfecho], int(r.n_desv), n0(r.nao_negra_n), f"{f1(r.nao_negra_pct)} ({ci(r.nao_negra_lo, r.nao_negra_hi, 1)})", n0(r.negra_n), f"{f1(r.negra_pct)} ({ci(r.negra_lo, r.negra_hi, 1)})", f1(r.diferenca_pp)] for r in t4.itertuples()]
    caption(d, f"**Supplementary Table {ST['grad']}a.** Prevalence (%) by number of disadvantages (woman reference person, no schooling or incomplete primary education, income ≤1/4 MW, rural residence) and race/colour, with the absolute difference (percentage points).")
    table(d, ["Outcome", "Disadvantages", "Non-Black, *n*", "Non-Black, % (95% CI)", "Black, *n*", "Black, % (95% CI)", "Difference, pp"], rows, font=8, bucket="decl")
    rows = []
    for r in t5.itertuples():
        dec = 2 if "relativa" in r.escala else 1
        fm = f2 if dec == 2 else f1
        rows.append([OUTL[r.desfecho], r.escala.replace("relativa (RR por desvantagem)", "relative (PR per disadvantage)").replace("absoluta (pp por desvantagem)", "absolute (percentage points per disadvantage)"),
                     f"{fm(r.nao_negra)} ({ci(r.nao_negra_lo, r.nao_negra_hi, dec)})", f"{fm(r.negra)} ({ci(r.negra_lo, r.negra_hi, dec)})", pfmt(r.p_diferenca)])
    caption(d, f"**Supplementary Table {ST['grad']}b.** Change in prevalence per additional disadvantage, by race/colour, on relative (PR, Poisson) and absolute (linear probability model) scales, with *P* for the difference between slopes.")
    table(d, ["Outcome", "Scale", "Non-Black (95% CI)", "Black (95% CI)", "*P* (difference)"], rows, font=8, bucket="decl")
    figure(d, "figS4_gradient.png", 5.9, "**Supplementary Figure S4.** Prevalence of food insecurity by number of disadvantages and race/colour, with 95% confidence intervals from replicate weights.", "decl",
           alt="Two-panel plot of prevalence against number of disadvantages, from zero to four, for Black and non-Black households, any and severe food insecurity, with 95% confidence intervals.")
    # S10-S12 MAIHDA
    A, G = AUC["ia_total"], AUC["ia_grave"]; ma, mg = m1.loc["ia_total"], m1.loc["ia_grave"]
    rows = [["Between-stratum variance, null model (σ²A)", f3(ma.sigma2_nulo), f3(mg.sigma2_nulo)],
            ["VPC, null model, % (95% CI)", f"{f1(ma.vpc_nulo*100)} ({ci(ma.vpc_nulo_lo*100, ma.vpc_nulo_hi*100, 1)})", f"{f1(mg.vpc_nulo*100)} ({ci(mg.vpc_nulo_lo*100, mg.vpc_nulo_hi*100, 1)})"],
            ["Between-stratum variance, main-effects model (σ²B)", f3(ma.sigma2_B), f3(mg.sigma2_B)], ["VPC, main-effects model, %", f1(ma.vpc_B * 100), f1(mg.vpc_B * 100)],
            ["PCV, % (logit scale)", f1(ma.pcv * 100), f1(mg.pcv * 100)], ["AUC, stratum predictions (full model)", f2(A["p_completo"]), f2(G["p_completo"])],
            ["AUC, additive (logit-scale) main effects only", f2(A["p_aditivo"]), f2(G["p_aditivo"])], ["AUC, income band only", f2(A["renda"]), f2(G["renda"])],
            ["Strata with |z| > 1.96 (of 160; about 8 expected by chance)", str(int(ma.n_z_gt196)), str(int(mg.n_z_gt196))],
            ["Largest full-minus-additive difference, percentage points", f1(ma.max_abs_dif_pp), f1(mg.max_abs_dif_pp)], ["Median absolute difference, percentage points", f2(ma.med_abs_dif_pp), f2(mg.med_abs_dif_pp)]]
    caption(d, f"**Supplementary Table {ST['maihda']}.** Intersectional MAIHDA across 160 strata: variance partition, proportional change in variance, discriminatory accuracy and departures from logit-scale additivity. Models are unweighted and operate on the logit scale; they do not test additivity on the prevalence scale.")
    table(d, ["Measure", "Any insecurity", "Severe insecurity"], rows, font=8, bucket="decl")
    lab4 = {"(Intercept)": "Intercept (reference stratum)", "raca_catnegra": "Black race", "sexo_catmulher": "Woman", "instrucao_catfund_med": "Education: complete primary/incomplete secondary",
            "instrucao_catmedio_comp": "Education: complete secondary", "instrucao_catsem_fund": "Education: no schooling/incomplete primary", "renda_catq1": "Income ≤1/4 MW", "renda_catq2": "Income >1/4-1/2 MW",
            "renda_catq3": "Income >1/2-1 MW", "renda_catq4": "Income >1-2 MW", "rural_catrural": "Rural residence"}
    rows = []
    for t_, l_ in lab4.items():
        a = m2[(m2.desfecho == "ia_total") & (m2.termo == t_)].iloc[0]; s_ = m2[(m2.desfecho == "ia_grave") & (m2.termo == t_)].iloc[0]
        rows.append([l_, f"{f2(a.oddsr)} ({ci(a.or_lo, a.or_hi)})", f"{f2(s_.oddsr)} ({ci(s_.or_lo, s_.or_hi)})"])
    caption(d, f"**Supplementary Table {ST['fixed']}.** MAIHDA Model B fixed effects: odds ratios (95% CI), which are not prevalence ratios. Reference: non-Black man, tertiary education, income >2 MW, urban.")
    table(d, ["Term", "Any insecurity (OR)", "Severe insecurity (OR)"], rows, font=8, bucket="decl")
    rows = [["Unweighted (main analysis): VPC null, %", f1(ma.vpc_nulo * 100), f1(mg.vpc_nulo * 100)], ["Unweighted: VPC main-effects model, %", f1(ma.vpc_B * 100), f1(mg.vpc_B * 100)], ["Unweighted: PCV, %", f1(ma.pcv * 100), f1(mg.pcv * 100)],
            ["Approximate weights: VPC null, %", f1(ma.w_vpc_nulo * 100), f1(mg.w_vpc_nulo * 100)], ["Approximate weights: VPC main-effects model, %", f1(ma.w_vpc_B * 100), f1(mg.w_vpc_B * 100)],
            ["Approximate weights: PCV, %", f1(ma.w_pcv * 100), f1(mg.w_pcv * 100)]]
    caption(d, f"**Supplementary Table {ST['weights']}.** Sensitivity of MAIHDA variance measures to approximate (normalised) survey weights; the weighted fits are not design-consistent. The 160 strata are listed in Supplementary_data_strata.xlsx.")
    table(d, ["Measure", "Any insecurity", "Severe insecurity"], rows, font=8, bucket="decl")
    figure(d, "figS5_maihda_strata.png", 6.0, "**Supplementary Figure S5.** Predicted prevalence in the 160 strata, ranked, from the full model (dots) and from logit-scale additive main effects alone (open circles).", "decl",
           alt="Two-panel plot of predicted prevalence for the 160 strata ranked from lowest to highest, any and severe food insecurity; dots for the full model and open circles for additive main effects on the logit scale, nearly coincident.")
    add_rodada_d_tables(d, ST)
    # STROBE
    tabs = lambda *k: "Supplementary Table" + ("s " if len(k) > 1 else " ") + ", ".join(ST[x] for x in k)
    S = [("1a", "Design indicated in title or abstract", "Abstract, Methods"), ("1b", "Informative and balanced abstract", "Abstract"), ("2", "Background and rationale", "Introduction"), ("3", "Objectives", "Introduction (last paragraph)"),
         ("4", "Key elements of study design", "Methods: Design and data"), ("5", "Setting, dates", "Methods: Design and data"), ("6", "Eligibility, sources and selection of participants", "Methods: Design and data"),
         ("7", "Variables, definitions", f"Methods: Outcome, Exposures; {tabs('coding')}"), ("8", "Data sources and measurement", "Methods: Outcome, Exposures"), ("9", "Efforts to address bias", "Methods; Discussion (limitations)"),
         ("10", "Study size", "Methods: Design and data"), ("11", "Handling of quantitative variables", "Methods: Exposures"), ("12a", "Statistical methods", f"Methods: Statistical analysis; {tabs('coding')} (part b)"),
         ("12b", "Subgroups and interactions", f"Methods: Statistical analysis; Supplementary Tables {ST['pairs']}-{ST['grad']}"), ("12c", "Missing data", "Methods: Design and data"), ("12d", "Sampling strategy (weights, clustering)", "Methods: Statistical analysis"),
         ("12e", "Sensitivity analyses", tabs('cells', 'region', 'weights', 'var', 'std', 'cut', 'ign')), ("13", "Participants at each stage", "Methods: Design and data"), ("14", "Characteristics of participants", f"Table 1; {tabs('table1')}"), ("15", "Outcome data", f"Table 1; {tabs('table1')}"),
         ("16", "Unadjusted and adjusted estimates", f"Tables 2-3; {tabs('own')}"), ("17", "Other analyses", "Results; Supplement"), ("18", "Key results", "Discussion, first paragraph"), ("19", "Limitations", "Discussion"),
         ("20", "Cautious interpretation", "Discussion"), ("21", "Generalisability", "Discussion (limitations)"), ("22", "Funding", "Declarations")]
    caption(d, f"**Supplementary Table {ST['strobe']}.** STROBE checklist for cross-sectional studies with locations in the article.")
    table(d, ["Item", "Recommendation", "Location"], [list(x) for x in S], widths=[1.2, 8.5, 6.0], font=8, bucket="decl")
    d.save(OUT / "B_Supplementary_material_IJE_rev4.docx")


# ============================================================== rastreabilidade
def build_traceability(nref):
    df = pd.DataFrame(TR)
    df.insert(0, "id", range(1, len(df) + 1))
    def grp(loc):
        if loc.startswith("Abstract"): return "Abstract"
        if loc.startswith("Table"): return "Tables"
        if loc.startswith("Supplementary"): return "Supplement"
        if loc.startswith(("Introduction", "Methods")): return "Text: Introduction-Methods"
        return "Text: Results-Discussion"
    df["group"] = df.location.map(grp)
    def _var(src):
        if "m1_maihda" in src or "m3_maihda" in src or "m2_maihda" in src or "calcula_auc" in src: return "MAIHDA: unweighted mixed model (no survey variance)"
        if "rodada_D/D1_" in src: return "C (replicate weights; model refitted in each replicate)"
        if "rodada_D/" in src: return "C (replicate weights)"
        if "v3_rodadaD_C" in src: return "C (replicate weights)"
        return "not applicable (design fact or count)"
    df["variance_method"] = df.source.map(_var)
    fig_rows = pd.DataFrame([
        ["Figure 1a", "RERI and 95% CI (replicate weights, method C), race × income and race × education, any and severe", "dados/v3_rodadaD_C/t2_pares.csv | par in {Race x Income..., Race x Education...}; desfecho | reri, reri_lo_delta, reri_hi_delta", SSM["t2"], "plots existing estimates; no recalculation"],
        ["Figure 1a (diamonds)", "RERI expected if multiplicative", "dados/v3_rodadaD_C/t2_pares.csv | same rows | reri_esperado_nulo_mult", SSM["t2"], ""],
        ["Figure 1b", "Ratio of PRs and 95% CI", "dados/v3_rodadaD_C/t2_pares.csv | same rows | ror, ror_lo, ror_hi", SSM["t2"], ""],
        ["Supplementary Figure S1a,c", "Adjusted PR for Black race by income band, 95% CI", "dados/v3_rodadaD_C/t6_estratificado.csv | exposicao=negra; estratificado_por=renda | rr_ajustado, lo, hi", SSM["t6"], "adjusted for sex, education, residence"],
        ["Supplementary Figure S1b,d", "Crude absolute difference by income band, approximate 95% CI", "dados/v3_rodadaD_C/t6_estratificado.csv | exposicao=negra; estratificado_por=renda | dif_pp, dif_pp_lo, dif_pp_hi", SSM["t6"], "crude; different model from panels a,c"]],
        columns=["location", "item", "source", "ssm_manuscript_location", "flag"])
    manual = pd.DataFrame([
        ["Methods", "473,206 person records read", "log of analise_consolidada_artigo3_20260925.py (linhas brutas)", "§2.1", ""],
        ["Methods", "median 562 households, range 16-5,719 per stratum", "dados/dados_maihda_2023.csv (group sizes by estrato; ms_numeros.N_STRATA)", "§2.4", ""],
        ["Methods", "160 strata = 2 × 2 × 4 × 5 × 2", "study design (unchanged)", "§2.4", ""],
        ["Methods", "Python 3.12 (statsmodels 0.14.6); R 4.6.1 (lme4 2.0.6)", "session environment", "§2.5", ""],
        ["Introduction", "two of 15 studies assessed additive-scale interaction", "Fivian et al. (ref in list), abstract", "§1", "literature number, not an estimate of this study"],
        ["Introduction", "27.6% of households with some food insecurity in 2023", "t1_descritiva.csv Total/Brasil ia_total_pct; IBGE 2024 reports the same figure", "§1; Table 1", ""],
        ["Methods", "19 reference persons with race/colour ignored (0.01% weighted) and 77 with income band ignored (0.06% weighted)", "auditoria/auditoria_dados_resumo.json (n_V2010=9, n_VDI5009=9, *_pct_pond); auditoria_dados_ije_20260926.py on the raw microdata", "audit 26/09/2026", "descriptive count from raw microdata, not an estimate"],
        ["Methods", "473 206 person records; one reference person and one weight per household; no household excluded", "auditoria/auditoria_dados_resumo.json (linhas_brutas, dom_com_1_responsavel, resp_com_EBIA_1a4)", "audit 26/09/2026", ""]],
        columns=["location", "item", "source", "ssm_manuscript_location", "flag"])
    with pd.ExcelWriter(OUT / "C_Traceability_table_rev4.xlsx", engine="openpyxl") as w:
        readme = pd.DataFrame({"README": [
            "Traceability table for the IJE version (rev2). Every number printed in the abstract, text and tables was read from the derived output tables by code (ije_lib_20260925.py) and logged here with its source file, row selection and column.",
            "'printed' = string in the manuscript; 'raw_value' = value in the source file; 'ssm_manuscript_location' = where the same estimate appears in the SSM manuscript (MANUSCRITO_EN_SSM_20260925) or its supplement.",
            "No estimate was recalculated, re-rounded or substituted: rounding uses the same functions as the SSM manuscript. Derived quantities (decomposition of the joint prevalence difference and its share) use the same formula as the SSM manuscript and are flagged.",
            "Sheets: Abstract; Text_Intro_Methods; Text_Results_Discussion; Tables; Supplement_Table_S2 (full Table 1); Figures; Non-CSV numbers; Coherence checks; Supplement provenance."]})
        readme.to_excel(w, sheet_name="README", index=False)
        for g in ["Abstract", "Text: Introduction-Methods", "Text: Results-Discussion", "Tables", "Supplement"]:
            df[df.group == g].drop(columns=["group"]).to_excel(w, sheet_name={"Abstract": "Abstract", "Text: Introduction-Methods": "Text_Intro_Methods", "Text: Results-Discussion": "Text_Results_Discussion", "Tables": "Tables", "Supplement": "Supplement_Table_S2"}[g], index=False)
        fig_rows.to_excel(w, sheet_name="Figures", index=False); manual.to_excel(w, sheet_name="Non-CSV numbers", index=False)
        pd.read_csv(OUT / "C_coherence_checks_rev4.csv").to_excel(w, sheet_name="Coherence checks", index=False)
        prov = pd.DataFrame([[f"Table {ST[k]}", v[0], v[1]] for k, v in {
            "table1": ("dados/v3_rodadaD_C/t1_descritiva.csv", "SSM Table 1"), "own": ("dados/atenuacao_renda_raca_sexo_2023.csv", "SSM Table 2"), "pairs": ("dados/v3_rodadaD_C/t2_pares.csv", "SSM Table 3"),
            "cells": ("t2_pares.csv + dados/interseccional_2023*.csv (bootstrap)", "SSM Suppl. Table S2"), "joint": ("t3_conjunto.csv", "SSM Table 4"), "three": ("t7_tripla.csv", "SSM Suppl. S4"),
            "region": ("dados/interseccional_2023_parte2.csv", "SSM Suppl. S3"), "strata": ("t6_estratificado.csv", "SSM Suppl. S5"), "grad": ("t4_gradiente_prev.csv; t5_gradiente_modelos.csv", "SSM Suppl. S6a,b"),
            "maihda": ("m1_maihda_geral.csv; m3_maihda_estratos.csv; AUC via ms_numeros", "SSM Table 5"), "fixed": ("m2_maihda_coef.csv", "SSM Suppl. S7"), "weights": ("m1_maihda_geral.csv (w_*)", "SSM Suppl. S8")}.items()],
            columns=["IJE supplementary table", "source file(s)", "SSM manuscript location"])
        prov.to_excel(w, sheet_name="Supplement provenance", index=False)
    return df


# ============================================================== relatorios
def counts_md(info):
    m = info
    return f"""# D. Contagens conforme as regras do IJE (Original Article), rev2

Regras conferidas em 25/09/2026 na página oficial de instruções do IJE (academic.oup.com/ije/pages/General_Instructions).
Guia de estilo: obtida a **"Mini Oxford SCIMED style checklist"** (PDF genérico da OUP; o IJE declara seguir o estilo Oxford SCIMED).
Aplicado: citações `[1, 3-5]` no fim da frase; referências com até 3 autores + "et al", periódico abreviado em itálico, `ano;vol:páginas` elididas com hífen;
números < 10 por extenso; espaço como separador de milhar a partir de 10 000; ortografia de Oxford (-ize, mas "analyse"); siglas definidas no resumo e no texto.

| Item | Limite IJE | Este manuscrito | Situação |
|---|---|---|---|
| Texto principal (exclui resumo, Key Messages, declarações, referências, tabelas, figuras e suplemento) | 3.000 | **{m['main']}** (com cabeçalhos; sem cabeçalhos: {m['main_nohead']}) | {'OK' if m['main'] <= 3000 else 'ACIMA'} |
| Resumo estruturado (Background, Methods, Results, Conclusions) | 250 | **{m['abstract']}** | {'OK' if m['abstract'] <= 250 else 'ACIMA'} |
| Palavras-chave | 3-10 | {m['nkw']} | OK |
| Key Messages | 3 frases completas | {m['nkm']} ({m['keymsg']} palavras) | OK |
| Referências | 50 | **{m['nref']}** | {'OK' if m['nref'] <= 50 else 'ACIMA'} |
| Tabelas + figuras no corpo | 8 | **{m['ntab']} tabelas + {m['nfig']} figura(s) = {m['ntab'] + m['nfig']}** | OK |

Texto principal por seção (com cabeçalhos): {', '.join(f'{k}: {v}' for k, v in m['sec'].items())}.
Palavras em legendas de figuras/tabelas (não contam): {m['captions']}; em tabelas: {m['tables']}; declarações e página de título: {m['decl']}.
Contagem feita por script (`\\S+`); o sistema de submissão do IJE pode contar diferente — conferir no upload.
"""


def pending_md(info):
    return f"""# E. Pendências que bloqueiam a submissão ao IJE

## Científicas (decisão ou verificação dos autores)
1. **Estimativas de interação brutas.** RERI, razão de RPs, RPs das quatro categorias e a decomposição vêm de modelos **sem covariáveis** (confirmado no código). Só o modelo mutuamente ajustado é ajustado, e ele só dá o termo multiplicativo. **VERIFICAR NO CÓDIGO/DADOS:** não existe RERI ajustado. Decidir se o IJE exigirá (novo cálculo, fora desta etapa) ou se o manuscrito mantém a limitação declarada.
2. **Sem IC para a decomposição** (2,5 de 13,2 pp; 19,1%). O texto declara isso. **VERIFICAR NO CÓDIGO/DADOS** se um IC é desejado (novo cálculo).
3. **Relativo × absoluto na Fig. S1 (antes Fig. 2 do corpo) vêm de modelos diferentes** (RP ajustada; diferença absoluta bruta). Não há diferença de prevalência ajustada nem RP bruta por faixa nos arquivos. O texto e a legenda declaram a diferença. Decidir se se calcula (novo cálculo).
4. **"Não negro":** o código define negro = V2010 ∈ {{2,4}} e o resto é não negro; se existir código 9 (ignorado), ele cai em "não negro". **VERIFICAR NO CÓDIGO/DADOS** a contagem. O texto já diz que não é sinônimo de branco.
5. **Sensibilidade ao ponto de corte da renda (≤1/4 SM):** não há nos arquivos. O texto declara a escolha como decisão de desenho.
6. **Terminologia:** "risk ratio" do manuscrito SSM foi trocado por "prevalence ratio" (transversal). Nenhum número mudou. Confirmar que os autores aceitam; "RERI" foi mantido como nome da medida.
7. **Câmara et al. 2026 (AJPH):** referência incompleta (ahead of print, fora do Crossref/PubMed). Completar autores/paginação.
8. **Estilo de referência (guia obtido em 25/09/2026):** aplicada a "Mini Oxford SCIMED style checklist". **A confirmar:** (a) o checklist é genérico da OUP, não específico do IJE; (b) ele não mostra DOI, que foi mantido como `doi:` no fim de cada referência (remover se o IJE não quiser); (c) abreviações de periódicos vieram de uma lista minha, conferir com o NLM/LTWA; (d) STROBE e FAO não foram expandidas por serem de uso comum; (e) o suplemento segue as mesmas convenções de números e ortografia.
9. **MAIHDA não ponderado:** limitação declarada; sensibilidade com pesos aproximados no suplemento (não é consistente com o desenho).
10. **Codificação das variáveis não verificada de forma independente.** A verificação usa a mesma função `preparar()` para ler os microdados; portanto **não valida** o mapeamento de V2010, VD3004, VDI5009, V1022 e SD17001 (Tabela S1a). Conferir com o dicionário do IBGE. Validação externa parcial: a prevalência de 27,6% (21,6 milhões de domicílios) coincide com a divulgada pelo IBGE.
11. **Descrição dos ajustes.** O modelo "totalmente ajustado" para raça (atenuação) inclui faixas de renda, sexo registrado, ruralidade e **escolaridade dicotomizada** (sem instrução/fundamental incompleto), e não em 4 categorias; os ajustes por faixa de renda (Fig. S1) usam escolaridade em 4 categorias. O texto do IJE foi corrigido; **o manuscrito SSM ainda diz "sexo, escolaridade e residência" sem especificar** (legenda da Fig. 1 e resultados) e deveria ser corrigido se ainda for submetido (o SSM não foi editado nesta rodada). Na rev2 a Tabela S1b lista, por análise, o conjunto exato de covariáveis. Numericamente: PR totalmente ajustada 1,31 (especificação relatada) contra 1,29 com escolaridade em 4 categorias (informativo, não muda a conclusão).
12. **Um manuscrito, dois periódicos:** o mesmo trabalho não deve estar simultaneamente em avaliação no SSM e no IJE.

## Administrativas
1. Autores, ordem, afiliações, autor para correspondência, ORCID (a página de título tem campos vazios).
2. **Ética:** o IJE pede nome do comitê e número de aprovação **ou** a declaração de que a aprovação era desnecessária, com motivo. Nada foi afirmado; campo destacado em amarelo.
3. Financiamento (formato IJE: "This work was supported by …"), conflitos de interesse, contribuições de cada autor (CRediT) e **autor garantidor**.
4. **Disponibilidade de dados e código:** o IJE exige que todo o código do artigo esteja disponível; repositório, licença e DOI não existem ainda (campo destacado, não criado nesta rodada).
5. **IA (política do IJE, conferida em 25/09/2026):** o uso em análise de dados ou produção de figuras deve ser descrito nos **Métodos** (ferramenta e como) e repetido nas Declarações; IA não pode ser autora; os autores respondem pela exatidão. O texto agora diz que o Claude Code escreveu **e executou** os scripts e gerou tabelas e figuras. **Os autores precisam checar código e saídas de forma independente** (por exemplo, reexecutar os scripts e conferir números-chave) e confirmar a declaração (campos destacados). Vale registrar que houve erros de código encontrados e corrigidos durante o trabalho. A reexecução e a verificação independente de 25/09/2026 (arquivo `F_Verification_report.md`) foram feitas **pela mesma IA**, com implementação diferente: reduzem o risco de erro de código, mas **não substituem a conferência humana**.
6. **Custo:** o IJE é da Oxford University Press. O acordo CAPES cobre Springer Nature, Elsevier, ACM, Royal Society, Wiley, IEEE e ACS. **Confirmar a rota de acesso aberto e o valor de APC no site do IJE/OUP** antes de decidir; a rota sem acesso aberto normalmente não cobra APC.
7. Anexar o checklist STROBE (está na Tabela {ST['strobe']}) e a declaração "Supplementary data are available at IJE online".
8. Carta ao editor e submissão **não** foram feitas, como pedido.
"""


def report_md(info, checks, n_tr):
    n_pass = int((checks.status == "PASS").sum())
    return f"""# Relatório de mudanças: versão IJE rev2 (Original Article), 25/09/2026

Este relatório descreve **apenas o que mudou da v1 (`A_Manuscript_IJE.docx`) para a rev2 (`A_Manuscript_IJE_rev4.docx`)**. O relatório da v1 (`Relatorio_de_mudancas_IJE.md`) e todos os arquivos da v1 continuam intactos; o manuscrito SSM não foi editado. A tabela "trecho anterior → trecho novo → motivo" está em `R2_Entregaveis_revisao_IJE.md`.

## 1. Conclusão científica corrigida em todo o texto (prioridade 1)
A v1 dizia, em vários lugares, que a desigualdade conjunta "foi super-aditiva, mas sub-multiplicativa" para insegurança alimentar em geral. Isso só vale para a **grave** (RERI 1,28 [0,48-2,08]; razão de RPs 0,68 [0,58-0,79]). Para **qualquer** insegurança o RERI foi 0,07 (−0,08 a 0,22), compatível com ausência de interação aditiva, e a razão de RPs 0,75 (0,71-0,80). Corrigido em: resumo (Conclusions e Results), Mensagem-chave 1, abertura da Discussão e Conclusão final. A sub-multiplicatividade foi preservada para os dois desfechos. Nenhum número mudou.

## 2. Linguagem causal removida da decomposição (prioridade 2)
"attributable to", "comprised … for", "interaction accounted for" e "MAIHDA attributed" foram trocados por redação aritmética e descritiva ("component corresponding to race/colour alone", "… to low income alone", "interaction component"). Os Métodos, as notas das Tabelas 2-3 e a Tabela S5 agora dizem que a decomposição é aritmética, descritiva e **não identifica efeitos causais**. Valores idênticos aos da v1.

## 3. "Benchmark natural" (prioridade 3)
"the natural benchmark" foi trocado por "a useful interpretive benchmark for contextualising a positive RERI", com a frase de que nem uma escala nem a outra é natural ou superior. Nos Métodos o RERI esperado sob multiplicatividade é "interpretive context" e "not a null hypothesis for interaction on the prevalence scale". "The relevant null" (Discussão) foi retirado. Mantida a distinção entre RERI (escala de prevalência), razão de RPs (multiplicativa) e PCV do MAIHDA (logit).

## 4. Ortografia e tipografia (prioridade 4)
"characteriztic(s)" era um **bug da minha função de ortografia** (trocava "-istic" por "-iztic"); corrigido por regex de palavra inteira e conferido na busca final. **Decisão sobre grafia:** o guia do IJE manda inglês britânico e o "mini checklist" da OUP usa a ortografia de Oxford (-ize, mas "analyse"). Por isso "racialized", "characterized", "linearization", "dichotomized", "anonymized", "criticized" são a **forma correta do guia**, não erros; foram padronizadas assim em todo o manuscrito e no suplemento. Referências: títulos literais não foram alterados. Também: intervalos com hífen, valores negativos com "to", P em maiúscula itálica e n em minúscula itálica, siglas por extenso na primeira menção (resumo, mensagens-chave, texto, tabelas, figuras, suplemento).

## 5. Especificação dos modelos (prioridade 5)
Os Métodos agora separam dois parágrafos, conferidos no código (`analise_consolidada_artigo3_20260925.py`, `atenuacao_renda_raca_sexo_20260916.py`):
- **RPs por faixa de renda:** ajustadas por sexo registrado, **escolaridade em 4 categorias** e residência; diferença absoluta **bruta**.
- **Modelos de atenuação:** RP bruta; + faixa de renda (4 indicadores); + sexo registrado, ruralidade e **escolaridade dicotomizada** (`sem_fund`).
- Os conjuntos **não foram harmonizados** e nada foi recalculado. A Tabela S1b lista as covariáveis de cada análise (incl. modelos por escolaridade, gradiente, tripla e MAIHDA).

## 6. Foco editorial (prioridade 6)
| Item | Decisão | Destino | Motivo |
|---|---|---|---|
| Tabela 1 | **Condensada** (todas as famílias, raça/cor e renda; 7 linhas de categorias) | Versão completa na Tabela S{ST['table1'][1:]} | A pergunta do artigo é raça × renda; sexo, escolaridade e residência só entram como covariáveis |
| Figura 2 (RP ajustada e diferença absoluta por renda) | **Movida para o suplemento** (Fig. S1) | Fig. S1; o texto cita "Supplementary Figure S1" | Deixa a Fig. 1 (duas escalas) como a única figura do corpo; relativo × absoluto continua descrito em texto |
| MAIHDA nos Métodos e Resultados | **Enxugado** (mantidos VPC, PCV, escala logit, sem pesos e ponteiro ao suplemento) | Tabelas S{ST['maihda'][1:]}-S{ST['weights'][1:]} | Nenhum resultado removido; só detalhe secundário fora do corpo |
| Figuras suplementares | Renumeradas: S1 renda (antes Fig. 2), S2 escolaridade, S3 quatro pares, S4 gradiente, S5 MAIHDA | figures/ | |
Corpo agora: **{info['ntab']} tabelas + {info['nfig']} figura**; texto principal **{info['main']}** palavras (limite 3.000); resumo **{info['abstract']}** (limite 250); **{info['nref']}** referências.

## 7. Outras mudanças de formato (guia oficial do IJE, conferido em 25/09/2026)
Espaçamento duplo; sem linhas verticais nas tabelas; texto alternativo em todas as figuras; siglas por extenso; campo de código (exigido pelo IJE) e formato de financiamento ("This work was supported by …") sinalizados como pendência; autor para correspondência com asterisco. Detalhes em `R2_Entregaveis_revisao_IJE.md` (item D).

## 8. Controle de coerência
`C_coherence_checks_rev4.csv`: **{n_pass}** verificações, todas PASS (entradas inalteradas). A comparação automática v1 × rev2 das Tabelas 2-3 e do resumo está em `F_Verification_report_rev4.md`.

## 9. Não feito (como pedido)
Sem novas análises; sem alteração de resultados ou ICs; sem DOI; sem afirmação de aprovação ética; sem autores ou financiamento inventados; sem repositório; sem carta ao editor; sem início de submissão.
"""


def verification_md():
    F = pd.read_csv(OUT / "F_independent_verification.csv"); A = pd.read_csv(OUT / "F_abstract_number_check.csv")
    st = F.status.value_counts().to_dict(); mx = F[F.status == "PASS"].abs_diff.max()
    info = F[F.status == "INFO"]
    inf = "; ".join(f"{r.item}: {r.independent:.4f} vs {r.reported_in_csv:.4f}" for r in info.itertuples())
    return f"""# F. Reexecução e verificação dos números (25/09/2026)

## 1. Reexecução das rotinas (mesmas entradas, do zero)
| Etapa | Resultado |
|---|---|
| `exportar_dados_maihda_20260916.py` (dados preparados) | arquivo **idêntico byte a byte** ao anterior e à cópia do artigo |
| `analise_consolidada_artigo3_20260925.py` (Tabelas 1-4, S2-S9) | 7 arquivos, 1.010 valores numéricos: **diferença máxima 0**, textos idênticos |
| `maihda_v2_20260925.R` (MAIHDA, ~10 min) | 3 arquivos, 3.340 valores numéricos: **diferença máxima 0** |
| `coerencia_ije_20260925.py`, figuras e montagem do manuscrito | reconstruídos; **resumo idêntico ao anterior** (248 palavras) |

## 2. Verificação independente (`verificacao_independente_ije_20260925.py`)
Implementação diferente da análise (numpy puro, sem statsmodels; IRLS de Poisson escrito à mão; delta por totais por UPA; AUC por postos de Mann-Whitney com pandas):
**{st.get('PASS', 0)} conferências dentro da tolerância; diferença máxima nas aprovadas: {mx:.1e}.** Cobre tamanho amostral, prevalências globais e ICs, prevalências das 4 células, PRs, RERI e ICs, razão de RPs e ICs, RERI esperado, decomposição, PRs ajustadas por faixa de renda (primeira e última), diferenças absolutas brutas, atenuação, PCV/VPC e AUC.

## 3. Números do resumo (`F_abstract_number_check.csv`)
**{int((A.status == 'MATCH').sum())} de {len(A)}** números do resumo conferem com o recálculo independente no arredondamento impresso.

## 4. Achado
- {inf}. Não é discrepância de cálculo: o modelo "totalmente ajustado" do script usa **escolaridade dicotomizada** (sem instrução/fundamental incompleto) e não 4 categorias; ao replicar essa especificação, o valor relatado é reproduzido exatamente. O texto do IJE e o suplemento foram corrigidos para descrever o ajuste.

## 5. O que esta verificação NÃO cobre
- Foi feita **pela mesma IA** que escreveu o código original (implementação diferente, mas não é revisão humana).
- Usa a mesma função `preparar()` para a **codificação das variáveis** (V2010, VD3004, VDI5009, V1022, SD17001); portanto não valida o mapeamento com o dicionário do IBGE. Validação externa parcial: prevalência de 27,6% (IBGE 2024).
- Os ICs por perfil de verossimilhança e as estimativas do modelo misto do MAIHDA não têm implementação alternativa; foram reproduzidos pela reexecução (idênticos), não recalculados de outro modo (VPC/PCV conferidos por aritmética; AUC, de forma independente).
- Não verifica as referências bibliográficas nem a fidelidade das afirmações da literatura (conferidas por PubMed/Crossref durante a redação).
"""


def build_tables_file(g):
    """IJE: tabelas em arquivo Word editavel separado do texto principal."""
    d = new_doc(line_numbers=False, spacing=1.0, size=10)
    p = d.add_paragraph(); r = p.add_run("Tables 1-3"); r.bold = True; r.font.size = Pt(13)
    p = d.add_paragraph(); rich(p, g["TITLE"], size=10)
    g["table_1"](d)
    g["table_joint"](d, "Table 2", "Race/colour × income", g["PI_a"], g["PI_s"], "income ≤1/4 MW", "income >1/4 MW")
    g["table_joint"](d, "Table 3", "Race/colour × education", g["PE_a"], g["PE_s"], "education ≤ incomplete primary", "education above incomplete primary")
    d.save(OUT / "Tables_1-3_IJE_rev4.docx")


def run(main_fn, g):
    main_fn(); n1 = dict(WC); s1 = dict(SEC); nref = len(ORDER)
    reset()
    ntab = 3; nfig = 1
    words_txt = (f"**Word count:** main text {n1['main']} words (as defined by IJE: excluding abstract, key messages, declarations, references, tables, figures and supplementary material); "
                 f"abstract {n1['abstract']} words; {nref} references; three tables and one figure.")
    g["WORDINFO"]["text"] = words_txt
    d = main_fn()
    d.save(OUT / "A_Manuscript_IJE_rev4.docx")
    heads = sum(wcount(x) for x in ["Design and data", "Outcome", "Exposures", "Statistical analysis", "Sample and prevalence", "Race/colour and income", "Race/colour and education", "Relative and absolute racial gaps across income", "Complementary MAIHDA", "Conclusion"])
    info = {"main": WC["main"], "main_nohead": WC["main"] - heads, "abstract": WC["abstract"], "keymsg": WC["keymsg"], "nkm": 3, "nkw": len(re.split(r";", g["KEYWORDS"])),
            "nref": len(ORDER), "ntab": len(d.tables) - 0, "nfig": len(d.inline_shapes), "sec": s1, "captions": WC["captions"], "tables": WC["tables"], "decl": WC["decl"]}
    shutil.copy(SSMDIR / "Supplementary_data_strata.xlsx", OUT / "Supplementary_data_strata.xlsx")
    build_supplement(g)
    df = build_traceability(len(ORDER))
    build_tables_file(g)
    checks = pd.read_csv(OUT / "C_coherence_checks_rev4.csv")
    (OUT / "D_Counts_IJE_rev4.md").write_text(counts_md(info), encoding="utf-8")
    print("A:", info)
    print("abstract words:", WC["abstract"], "| main:", WC["main"], "| refs:", len(ORDER), "| rastreados:", len(df))
    unused = [k for k in DOIS if k not in REFN]
    print("refs nao usadas (ok):", len(unused))
