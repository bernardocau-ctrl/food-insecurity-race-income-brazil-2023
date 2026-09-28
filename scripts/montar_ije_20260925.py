# -*- coding: utf-8 -*-
"""
montar_ije_20260925.py

Versao IJE (Original Article) do Artigo 3. NAO altera o manuscrito SSM e NAO estima nada novo:
todo numero passa por ije_lib (leitura dos CSVs existentes, mesmo arredondamento do manuscrito SSM).
Gera em MANUSCRITO_IJE_20260925/:
  A_Manuscript_IJE.docx        titulo identificado + resumo + Key Messages + texto + declaracoes + referencias + tabelas
  B_Supplementary_material_IJE.docx
  C_Traceability_table.xlsx    (+ C_coherence_checks.csv, gerado por coerencia_ije_20260925.py)
  D_Counts_IJE.md
"""
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ije_lib_20260925 import *     # noqa

# ------------------------------------------------------------------ linhas de dados
tot = T1("Total", "Brasil"); blk = T1("Cor/raca", "negra (preta+parda)"); nbk = T1("Cor/raca", "nao negra")
i1 = T1("Renda pc", "q1"); i5 = T1("Renda pc", "q5"); e1 = T1("Instrucao", "sem_fund"); e4 = T1("Instrucao", "superior")
PI_a, PI_s = T2("Race x Income", "ia_total"), T2("Race x Income", "ia_grave")
PE_a, PE_s = T2("Race x Education", "ia_total"), T2("Race x Education", "ia_grave")
RAW = 473206
NUM = lambda x: str(int(x))
NW = lambda x: {"0": "none", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}.get(str(x), str(x))

import json
AUD = json.load(open(BASE / "MANUSCRITO_IJE_20260925" / "auditoria" / "auditoria_dados_resumo.json", encoding="utf-8"))
FIG1_ALT = "Two-panel plot with 95% confidence intervals. Panel a: relative excess risk due to interaction for race/colour by income and race/colour by education, any and severe food insecurity, with diamonds marking the value expected if joint effects were multiplicative. Panel b: ratio of prevalence ratios for the same contrasts, all below one."
WORDINFO = {"text": "**Word count:** ⟦filled at build time⟧"}
TITLE = "Race, income and household food insecurity in Brazil: joint disparities depend on the scale of interaction"
RUNNING = "Joint disparities and interaction scale in food insecurity"
KEYWORDS = "food insecurity; racial inequality; income; interaction; additive and multiplicative scales; intersectionality; multilevel analysis; Brazil"

AI_DECL = ("Claude (Anthropic; ⟦CONFIRM: model names, versions and dates of use⟧) was used for literature searching and for drafting and translating the manuscript, and Claude Code for writing and running the analysis code and producing the tables and figures (see Methods). "
           "⟦CONFIRM: authors reviewed and edited all AI-assisted content and take full responsibility for the accuracy and integrity of the manuscript⟧ Artificial intelligence (AI) is not listed as an author.")


# ------------------------------------------------------------------ resumo e mensagens
def abstract_parts():
    setloc("Abstract")
    bg = "Joint racial and socioeconomic disparities are often read as intersectional synergy, but interpretation depends on the interaction scale."
    me = (f"In {q1(tot,'n',n0)} Brazilian households (fourth quarter 2023), "
          f"survey-weighted models with replicate-weight variance estimated prevalence ratios (PR) for joint categories of race/colour (Black vs non-Black) and per capita income (≤1/4 vs >1/4 minimum wage), "
          f"the relative excess risk due to interaction (RERI), the ratio of PRs and the decomposition of the joint prevalence difference. "
          f"Standardized, education, cut-point and multilevel analyses were secondary.")
    re_ = (f"Prevalence was {q1pc(tot,'ia_total_pct','ia_total_lo','ia_total_hi')} for any and {q1pc(tot,'ia_grave_pct','ia_grave_lo','ia_grave_hi',short=True)} for severe insecurity. "
           f"Black households with income ≤1/4 minimum wage had a severe-insecurity PR of {q2ci(PI_s,'rr11','rr11_lo','rr11_hi')}; "
           f"RERI was {q2ci(PI_s,'reri','reri_lo_delta','reri_hi_delta',2,'tab')}, but the ratio of PRs was {q2ci(PI_s,'ror','ror_lo','ror_hi',2,'tab')} and the RERI expected if multiplicative {q2(PI_s,'reri_esperado_nulo_mult')}; "
           f"the interaction component was {qjdci(PI_s,3)} of {qjd(PI_s,0)} percentage points. "
           f"After standardization the RERI was {qstd('ia_grave','reri',dec=2,mode='tab')}. "
           f"For any insecurity, RERI was {q2ci(PI_a,'reri','reri_lo_delta','reri_hi_delta',2,'tab')} and the ratio of PRs {q2ci(PI_a,'ror','ror_lo','ror_hi',2,'tab')}. "
           f"Adjusted PRs for Black race were {q6ci('negra','renda','q1','ia_total','rr_ajustado','lo','hi',mode='sq')} in the lowest and "
           f"{q6ci('negra','renda','q5','ia_total','rr_ajustado','lo','hi',mode='sq')} in the highest income band, while crude absolute differences fell "
           f"({q6('negra','renda','q1','ia_total','dif_pp',f1)} to {q6('negra','renda','q5','ia_total','dif_pp',f1)} percentage points). "
           f"Unweighted multilevel main effects accounted for {qm1('ia_total','pcv',f1,100)}% and {qm1('ia_grave','pcv',f1,100)}% of between-stratum variance (logit).")
    re_ = re_.replace("95% CI", "95% confidence interval [CI]", 1)
    co = ("Joint racial and income disparities were super-additive for severe food insecurity, compatible with additivity for any at the primary cut-point, and sub-multiplicative for both. "
          "Both scales should be reported, with the multiplicative expectation as context.")
    return bg, me, re_, co


KEYMSG = [
    "In Brazil, the joint disparity in severe household food insecurity by race/colour and income was super-additive but sub-multiplicative, whereas for any food insecurity the RERI interval included zero at the primary income cut-point and the disparity was sub-multiplicative, so conclusions about synergy depend on the scale and the outcome.",
    "A positive relative excess risk due to interaction may usefully be read alongside the excess expected under multiplicative joint effects, the joint categories, the ratio of prevalence ratios and the absolute decomposition.",
    "Intersectional multilevel analysis operates on the logit scale, can describe stratum variation, and cannot by itself establish the absence of interaction on the prevalence scale.",
]


# ------------------------------------------------------------------ texto principal
def intro(d):
    CURSEC["s"] = "Introduction"; setloc("Introduction")
    para(d, f"Health inequalities are rarely one-dimensional: racialised groups are also disproportionately poor, and whether their joint disadvantage exceeds what each disadvantage predicts separately is a recurrent question in equity research, often framed as intersectionality {C('crenshaw1989','bauer2014')}. "
            f"Quantitatively, the answer depends on the scale. Interaction on the additive scale, the excess of joint prevalence over the sum of the separate excesses, bears directly on public health impact, whereas interaction on the multiplicative scale is what log-link and logit-link regression terms test {C('rothman1980','knol2012','vanderweele2014')}. "
            f"The two can disagree and reporting both is recommended, yet a scoping review of quantitative nutrition research found that only two of 15 studies using non-linear models assessed additive-scale interaction {C('knol2012','vanderweele2014','fivian2024')}.")
    para(d, f"A positive relative excess risk due to interaction (RERI) is readily read as synergy, but it is not evidence of it: when two exposures each carry a ratio above one, additivity is violated even if their effects are exactly multiplicative, so the excess expected under multiplicative joint effects is a useful interpretive benchmark for contextualising a positive RERI, although neither scale is the natural or superior standard {C('rothman1980','vanderweele2014')}. "
            f"Interaction can be absent on one scale and present on the other in the same data {C('reynolds2021')}. The joint disparity between the most and least advantaged groups can be decomposed into components corresponding to each exposure and their interaction {C('jackson2016')}. "
            f"Intersectional multilevel analysis of individual heterogeneity and discriminatory accuracy (MAIHDA) offers a third view, partitioning variance between strata on the logit scale {C('merlo2018','evans2018','evans2024a')}. "
            f"It has been criticized and defended, and its relation to additive-scale interaction is not obvious {C('wilkes2024','evans2024b','bashir2026')}.")
    para(d, f"In 2023, {q1(tot,'ia_total_pct',f1)}% of households reported some food insecurity {C('ibge2024')}. This followed a decline that took the country off the Hunger Map of the Food and Agriculture Organization (FAO), yet racial inequalities persisted {C('fao2025','luiz2026')}. "
            f"Brazilian studies find the highest prevalence among Black and Brown women {C('santos2023')}, and some report racial disparities that persist within strata of income {C('silva2022a','camara2026')}. To our knowledge, none compares additive and multiplicative interaction.")
    para(d, "We therefore asked how the interpretation of the joint disparity in household food insecurity by race/colour and household income, and secondarily by race/colour and education, depends on the scale of interaction. MAIHDA is complementary, not a test of mechanism.")


def methods(d):
    CURSEC["s"] = "Methods"; setloc("Methods")
    H2(d, "Design and data", True)
    para(d, f"This cross-sectional study used public-use microdata from the fourth quarter of 2023 of the Continuous National Household Sample Survey (PNADC), a probability survey of Brazilian households conducted by the Brazilian Institute of Geography and Statistics (IBGE) with a stratified, clustered design, which in that quarter carried a food security supplement {C('ibge2024')}. "
            f"The unit of analysis is the household, characterised by its reference person. The file held {n0(RAW)} person records. Each of the {q1(tot,'n',n0)} households had one reference person with a valid food insecurity classification and a survey weight, so no household was excluded. Reporting follows the Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) guideline {C('vonelm2007')}.")
    H2(d, "Outcome", True)
    para(d, f"IBGE classified households as secure or mildly, moderately or severely insecure with the Brazilian Food Insecurity Scale (EBIA), an experiential household scale validated in Brazil {C('perezescamilla2004')}. We analysed any insecurity (mild, moderate or severe) and severe insecurity, using the distributed classification. Measurement invariance across sex, race and education was supported in the 2013 survey {C('cezimbra2026a')}.")
    H2(d, "Exposures", True)
    para(d, f"Race/colour was self-reported in IBGE categories. We contrasted Black (pretos and pardos) with non-Black, a residual category comprising all other categories, including white, Asian and Indigenous people; it is not a synonym for white. Race/colour was recorded as ignored for {AUD['n_V2010=9']} reference persons, classified as non-Black ({AUD['V2010_9_ou_branco_classificado_como_nao_negro_pct_pond']:.2f}% of weighted households), and per capita income as ignored for {AUD['n_VDI5009=9']}, classified in the highest band, >2 MW ({AUD['VDI5009_9_ou_branco_pct_pond']:.2f}%). "
            f"Income was per capita household income in five bands of the monthly minimum wage (MW): ≤1/4, >1/4-1/2, >1/2-1, >1-2 and >2. The primary contrast dichotomised income at ≤1/4 versus >1/4 MW; the secondary contrast dichotomised the education of the reference person as no schooling or incomplete primary versus higher levels. "
            f"Recorded sex and urban or rural residence were covariates; recorded sex is not a measure of gender identity {C('heidari2016')}.")
    H2(d, "Statistical analysis", True)
    para(d, f"Estimates used the final survey weight and, except for the multilevel models, weighted Poisson regression {C('zou2004')}; because the outcome is common and the design cross-sectional, estimates are prevalence ratios (PR). "
            f"Variance was estimated with the 200 bootstrap replicate weights supplied with the microdata (V1028001-V1028200), recomputing every estimate, model and interval in each replicate (squared deviations from the full-sample estimate, divided by 199). "
            f"For comparison, we used clustering on primary sampling units alone and nested in strata (Estrato; a stratum with one unit was centred at the overall mean; Supplementary Table {ST['var']}).")
    para(d, f"*Joint categories and interaction.* For each contrast we classified households into four joint categories and estimated the PR of each against a common reference: non-Black households without the socioeconomic disadvantage. These models are crude: they contain no covariates. "
            f"On the additive scale we computed the RERI = PR11 − PR10 − PR01 + 1 {C('rothman1980','vanderweele2014')}, with 95% confidence intervals (CI) from the replicates. "
            f"On the multiplicative scale we report the ratio of PRs, PR11/(PR10 × PR01). For interpretive context we also report the RERI expected under exactly multiplicative joint effects, (PR10 − 1)(PR01 − 1); it is not a null hypothesis for interaction on the prevalence scale. "
            f"We also decomposed the joint prevalence difference (both disadvantages versus reference) into a component corresponding to race/colour alone (p10 − p00), one corresponding to the socioeconomic disadvantage alone (p01 − p00), and an interaction component, p11 − p10 − p01 + p00 {C('jackson2016')}. The interaction contrast equals the RERI multiplied by the reference prevalence, and component intervals come from the same replicates. The decomposition is arithmetic and descriptive and does not identify causal effects.")
    para(d, "*Racial gaps across income bands.* Within each of the five income bands we estimated the PR for Black race adjusted for recorded sex, education in four categories and residence (urban or rural), and the crude difference in prevalence in percentage points.")
    para(d, f"*Attenuation of the crude association.* In a separate set of models fitted to the whole sample we estimated the PR for Black race crudely, adjusted for income band (four indicators), and further adjusted for recorded sex, rural residence and low education (no schooling or incomplete primary, dichotomised). These analyses use different covariate sets (Supplementary Table {ST['coding']}). Attenuation is the proportional reduction of the crude log PR; it describes association and is not a mediation analysis.")
    para(d, f"*Sensitivity analyses.* We standardized the four joint-category prevalences to the sex, education (four categories) and residence distribution of the whole sample, using a weighted logistic model with the joint category and these covariates, averaging predicted probabilities with the category fixed (g-computation) and refitting in each replicate. This describes the disparity if the groups shared that composition, assuming homogeneous covariate effects on the logit scale; it is not a causal effect and does not remove confounding. "
            f"We also repeated the primary contrast with income cut-points of ≤1/2 and ≤1 MW and after excluding households with ignored race/colour or income (Supplementary Tables {ST['std']}-{ST['ign']}).")
    para(d, f"*MAIHDA.* We fitted intersectional MAIHDA models, without survey weights, to the 160 strata defined by race (two categories), sex (two), education (four), income (five) and residence (two), all occupied {C('merlo2018','evans2024a')}. "
            f"Logistic models with a stratum random intercept were fitted without covariates (Model A) and with the five characteristics as fixed effects (Model B). The variance partition coefficient (VPC) is the share of latent-scale variance between strata; the proportional change in variance (PCV) is the share of between-stratum variance accounted for, statistically, by additive main effects on the logit scale. "
            f"These models are not designed to test additivity on the prevalence scale; further results and sensitivity to approximate weights are in Supplementary Tables {ST['maihda']} and {ST['weights']}.")
    para(d, f"*Transparency.* The study was not pre-registered; the multiplicative expectation, the decomposition, the stratum-specific gaps, the gradients and the sensitivity analyses were added after inspecting initial results and are exploratory. "
            f"The replicate-weight variance was chosen after comparing three methods (Supplementary Table {ST['var']}). Other pairs, the mutually adjusted model, and three-way, regional and cumulative-disadvantage analyses are in Supplementary Tables {ST['pairs']}, {ST['joint']} and {ST['three']}-{ST['grad']}. Analyses used Python 3.12 and R 4.6.1 (lme4 2.0.6; survey 4.5 for validation). An artificial intelligence (AI) coding assistant (Claude Code, Anthropic) was used, under the authors' direction, to write and run the analysis scripts and to produce the tables and figures from the derived output files. ⟦CONFIRM: authors independently checked the code and outputs and retain control of the results⟧ Every number in this article was read from those output tables.")


def results(d):
    CURSEC["s"] = "Results"; setloc("Results 1")
    H2(d, "Sample and prevalence", True)
    para(d, f"The analytic sample comprised {q1(tot,'n',n0)} households. Weighted prevalence was {q1pc(tot,'ia_total_pct','ia_total_lo','ia_total_hi')} for any and {q1pc(tot,'ia_grave_pct','ia_grave_lo','ia_grave_hi')} for severe insecurity. "
            f"Of the reference persons, {q1(blk,'pct_pond_amostra',f1)}% were Black and {q1(i1,'pct_pond_amostra',f1)}% had income ≤1/4 MW per capita. Any insecurity ranged from {q1(i1,'ia_total_pct',f1)}% in the lowest to {q1(i5,'ia_total_pct',f1)}% in the highest income band and was {q1(blk,'ia_total_pct',f1)}% in Black and {q1(nbk,'ia_total_pct',f1)}% in non-Black households (Table 1).")
    table_1(d)
    setloc("Results 2")
    H2(d, "Race/colour and income", True)
    para(d, f"Prevalence of severe insecurity was {q2(PI_s,'p00',f1)}% in the reference group (non-Black, income >1/4 MW), {q2(PI_s,'p10',f1)}% in Black households above that income, {q2(PI_s,'p01',f1)}% in non-Black households at or below 1/4 MW and {q2(PI_s,'p11',f1)}% in Black households at or below 1/4 MW (Table 2), corresponding to PRs of "
            f"{q2ci(PI_s,'rr10','rr10_lo','rr10_hi')}, {q2ci(PI_s,'rr01','rr01_lo','rr01_hi')} and {q2ci(PI_s,'rr11','rr11_lo','rr11_hi')}. "
            f"The RERI was {q2ci(PI_s,'reri','reri_lo_delta','reri_hi_delta')}, yet the RERI expected under multiplicative joint effects was {q2(PI_s,'reri_esperado_nulo_mult')} and the ratio of PRs was {q2ci(PI_s,'ror','ror_lo','ror_hi')} (Figure 1): the joint PR was well above additive expectation and well below multiplicative expectation. "
            f"The joint prevalence difference was {qjdci(PI_s,0)} percentage points: the component corresponding to race/colour alone was {qjd(PI_s,1)}, that corresponding to low income alone {qjd(PI_s,2)}, and the interaction component {qjdci(PI_s,3)}, or {qshare(PI_s)}% of the joint difference.")
    para(d, f"For any insecurity, prevalences were {q2(PI_a,'p00',f1)}%, {q2(PI_a,'p10',f1)}%, {q2(PI_a,'p01',f1)}% and {q2(PI_a,'p11',f1)}%, with PRs of {q2ci(PI_a,'rr10','rr10_lo','rr10_hi')}, {q2ci(PI_a,'rr01','rr01_lo','rr01_hi')} and {q2ci(PI_a,'rr11','rr11_lo','rr11_hi')}. "
            f"The RERI was {q2ci(PI_a,'reri','reri_lo_delta','reri_hi_delta')}, compatible with no additive-scale interaction, against {q2(PI_a,'reri_esperado_nulo_mult')} expected if joint effects were multiplicative; the ratio of PRs was {q2ci(PI_a,'ror','ror_lo','ror_hi')}. "
            f"Of the joint difference of {qjd(PI_a,0)} points, the interaction component was {qjdci(PI_a,3)}.")
    table_joint(d, "Table 2", "Race/colour × income", PI_a, PI_s, "income ≤1/4 MW", "income >1/4 MW")
    figure(d, "fig1_interaction_scales.png", 6.2, alt=FIG1_ALT, cap="**Figure 1.** Interaction between race/colour and socioeconomic position on the additive and multiplicative scales. (a) Relative excess risk due to interaction (RERI) with 95% confidence interval (replicate weights); diamonds show the RERI expected if joint effects were multiplicative. (b) Ratio of prevalence ratios with 95% confidence interval (replicate weights). Crude, survey-weighted estimates; income ≤1/4 versus >1/4 minimum wage per capita; education no schooling or incomplete primary versus higher levels. MW, minimum wage; PR, prevalence ratio.")
    caption(d, "**Figure 1, alt text:** " + FIG1_ALT)
    setloc("Results 3")
    H2(d, "Race/colour and education", True)
    para(d, f"Results were similar for the secondary contrast (Table 3). For severe insecurity the RERI was {q2ci(PE_s,'reri','reri_lo_delta','reri_hi_delta')} against {q2(PE_s,'reri_esperado_nulo_mult')} expected, and the ratio of PRs {q2ci(PE_s,'ror','ror_lo','ror_hi')}. "
            f"Of the joint difference of {qjd(PE_s,0)} points, the interaction component was {qjdci(PE_s,3)}. For any insecurity the RERI was {q2ci(PE_a,'reri','reri_lo_delta','reri_hi_delta')}, with an interval that included zero, and the ratio of PRs {q2ci(PE_a,'ror','ror_lo','ror_hi')}.")
    table_joint(d, "Table 3", "Race/colour × education", PE_a, PE_s, "education ≤ incomplete primary", "education above incomplete primary")
    setloc("Results 4")
    H2(d, "Relative and absolute racial gaps across income", True)
    para(d, f"Across income bands (Supplementary Figure S1) the adjusted PR for Black race was {q6ci('negra','renda','q1','ia_total','rr_ajustado','lo','hi')} in the lowest band and {q6ci('negra','renda','q5','ia_total','rr_ajustado','lo','hi')} in the highest for any insecurity, and "
            f"{q6ci('negra','renda','q1','ia_grave','rr_ajustado','lo','hi')} and {q6ci('negra','renda','q5','ia_grave','rr_ajustado','lo','hi')} for severe insecurity, with a dip in the second band. The crude absolute difference in any insecurity fell from "
            f"{q6ci('negra','renda','q1','ia_total','dif_pp','dif_pp_lo','dif_pp_hi',1)} to {q6ci('negra','renda','q5','ia_total','dif_pp','dif_pp_lo','dif_pp_hi',1)} percentage points. "
            f"The crude PR for Black race was {qa('Negra','bruto','ia_total','rr')} for any insecurity, {qa('Negra','so_renda','ia_total','rr')} after adjustment for income band and {qaci('Negra','renda_e_demais','ia_total')} after further adjustment for recorded sex, low education and residence, an attenuation of the crude log PR of {qa('Negra','so_renda','ia_total','atenuacao_pct',f1)}% by income alone (Supplementary Table {ST['own']}).")
    setloc("Results 5")
    H2(d, "Sensitivity analyses", True)
    para(d, f"After standardization for recorded sex, education and residence, the RERI for severe insecurity was {qstd('ia_grave','reri',dec=2)} (crude {qstd('ia_grave','reri','bruto',dec=2,with_ci=False)}) and the ratio of PRs {qstd('ia_grave','ror',dec=2)}; for any insecurity the RERI was {qstd('ia_total','reri',dec=2)} (Supplementary Table {ST['std']}). "
            f"With income cut-points of ≤1/2 and ≤1 MW, the RERI for severe insecurity remained positive ({qcut('<=1/2 SM','ia_grave','reri',2,with_ci=False)} and {qcut('<=1 SM','ia_grave','reri',2,with_ci=False)}) and the ratio of PRs below one. For any insecurity it was {qcut('<=1/2 SM','ia_total','reri',2)} at ≤1/2 MW but {qcut('<=1 SM','ia_total','reri',2)} at ≤1 MW, so compatibility with additivity did not extend to that cut-point (Supplementary Table {ST['cut']}). "
            f"Excluding the {AUD['n_V2010=9']} households with ignored race/colour and {AUD['n_VDI5009=9']} with ignored income changed prevalences, PRs, RERI, ratio of PRs and absolute components of the joint categories by at most {qign_max(['prevalencia de celula','componente absoluto (pp)'])} percentage points or {qign_max(['PR','RERI','razao de PRs'])} units; prevalence in the highest income band, which contained the {AUD['n_VDI5009=9']}, changed by {qign_q5()} percentage points (Supplementary Table {ST['ign']}).")
    setloc("Results 6")
    H2(d, "Complementary MAIHDA", True)
    para(d, f"Strata carried {qm1pc('ia_total','vpc_nulo','vpc_nulo_lo','vpc_nulo_hi')} and {qm1pc('ia_grave','vpc_nulo','vpc_nulo_lo','vpc_nulo_hi',short=True)} of latent-scale variance in any and severe insecurity, falling to {qm1('ia_total','vpc_B',f1,100)}% and {qm1('ia_grave','vpc_B',f1,100)}% with main effects; the PCV was {qm1('ia_total','pcv',f1,100)}% and {qm1('ia_grave','pcv',f1,100)}%. "
            f"The largest prevalence-scale difference between full-model and main-effects predictions was {qm1('ia_total','max_abs_dif_pp',f1)} and {qm1('ia_grave','max_abs_dif_pp',f1)} percentage points (Supplementary Table {ST['maihda']}).")


def discussion(d):
    CURSEC["s"] = "Discussion"; setloc("Discussion")
    para(d, f"In a national survey of {q1(tot,'n',n0)} Brazilian households, the joint disparity in severe food insecurity by race/colour and income was super-additive (RERI {q2(PI_s,'reri')}) and sub-multiplicative (ratio of PRs {q2(PI_s,'ror')}). "
            f"For any food insecurity the RERI was {q2ci(PI_a,'reri','reri_lo_delta','reri_hi_delta')}, an interval that includes zero and is compatible with no additive-scale interaction at the primary cut-point, while the ratio of PRs was also below one ({q2(PI_a,'ror')}). "
            f"After standardization for sex, education and residence the severe-insecurity RERI was about half the crude value ({qstd('ia_grave','reri',dec=2,mode='br')}), which descriptively suggests that part of the crude excess coincides with group differences in composition. "
            f"The racial gap persisted at every income level, larger in relative and smaller in absolute terms at higher income, and in the multilevel analysis additive main effects accounted for nearly all between-stratum variance on the logit scale.")
    para(d, f"These results answer three different questions and should not be merged into a single verdict on synergy. The RERI and the decomposition of the joint prevalence difference ask whether joint prevalence exceeds the sum of separate excesses, the scale most directly related to the burden associated with combining disadvantages. The ratio of PRs asks whether it exceeds their product. "
            f"Under exact multiplicativity any two PRs above one yield a positive RERI, so a positive RERI does not by itself show departure from multiplicativity, which is why the multiplicative expectation is useful context. Here the observed RERI was below that expectation in both contrasts and for both outcomes (Tables 2 and 3), a pattern that may reflect weaker-than-multiplicative joint effects, ceiling effects or heterogeneity within crude categories, which these data cannot distinguish. "
            f"Additivity on the logit scale is multiplicativity on the odds, so a PCV near 100% is a statement about the log-odds scale. It does not establish additivity on the prevalence scale, where the interaction component corresponded to {qshare(PI_s)}% of the joint difference for severe insecurity, but neither does it contradict that finding, because the null hypotheses differ. We therefore treat MAIHDA as descriptive and complementary: it shows that stratum-level variation is largely accounted for by main effects on the logit scale, not that no joint excess exists.")
    para(d, f"None of these quantities is a causal effect or evidence of mechanism. Interaction, on any scale, describes how joint prevalence departs from a reference model; it depends on how exposures are dichotomised and on the reference group. An absolute contrast identifies where burden concentrates, which is useful for planning, whereas sub-multiplicativity says little about whether racism and poverty compound in people's lives {C('bauer2014')}. "
            f"Likewise, attenuation of the crude racial association by income describes association, not mediation: the two are entangled, and race/colour is a social classification that indexes, rather than measures, exposure to racism.")
    para(d, f"Relative measures are mechanically larger when baseline prevalence is lower, so a rising PR need not signal diminishing returns. The pattern is nonetheless consistent with reports that racial gaps in health persist or widen in relative terms at higher socioeconomic position {C('farmer2005','assari2018')}, and with evidence on food insecurity from Canada, the United States and Rio de Janeiro {C('dhunna2021','berning2024','camara2026')}. "
            f"Fundamental-cause theory and structural racism offer interpretations that these data cannot test {C('phelanlink2015','bailey2017','williams2019','werneck2016')}.")
    para(d, "The lesson is not specific to Brazil: wherever two exposures carry large prevalence ratios on a low baseline, a positive RERI is expected even without multiplicative interaction. Studies of joint disparities should show the joint categories, both interaction scales with the multiplicative expectation as context, and the absolute decomposition, and state the scale of any multilevel analysis.")
    para(d, f"Several limitations apply. First, the design is cross-sectional and the estimates are associations. Second, exposures describe the reference person whereas the outcome is household-level. Third, race/colour is dichotomised and non-Black is heterogeneous. "
            f"Fourth, the primary joint-category estimates are crude; the standardized analysis adjusts only for sex, education and residence, assumes homogeneous covariate effects on the logit scale and is descriptive, and the interaction share for any insecurity is imprecise (Supplementary Table {ST['comp']}). "
            f"Fifth, the relative and absolute gaps across income come from different models with different covariate sets. Sixth, income is current per capita income in bands, and the ≤1/4 MW cut-point is a design choice; the cut-point analyses were exploratory, and for any insecurity additive compatibility depended on the cut-point. "
            f"Seventh, the MAIHDA models are unweighted and variance measures are on the latent scale {C('bashir2026')}. Eighth, evidence of EBIA invariance is from 2013 and concerns single characteristics {C('cezimbra2026a')}. Finally, several analyses, including the variance method, were chosen or added after initial inspection, multiple comparisons were not adjusted, and the survey covers a single quarter.")


def conclusion(d):
    CURSEC["s"] = "Conclusion"; setloc("Conclusion")
    H2(d, "Conclusion", True)
    para(d, f"In Brazil in 2023, the joint racial and income disparity in severe household food insecurity was super-additive and sub-multiplicative, whereas for any food insecurity the RERI was {q2ci(PI_a,'reri','reri_lo_delta','reri_hi_delta')}, compatible with additivity at the primary cut-point, and the disparity was sub-multiplicative. Conclusions about intersectional synergy depend on the scale and the outcome, and should rest on joint categories with a common reference, both interaction scales, the multiplicative expectation as interpretive context and an absolute decomposition.")


# ------------------------------------------------------------------ tabelas
LAB1 = {"nao negra": "Non-Black", "negra (preta+parda)": "Black (preta or parda)", "homem": "Man", "mulher": "Woman", "sem_fund": "No schooling or incomplete primary",
        "fund_med": "Complete primary or incomplete secondary", "medio_comp": "Complete secondary", "superior": "Tertiary (complete or incomplete)", "q1": "≤1/4", "q2": ">1/4-1/2", "q3": ">1/2-1",
        "q4": ">1-2", "q5": ">2", "urbano": "Urban", "rural": "Rural"}


def table_1(d, full=False):
    setloc(f"Supplementary Table {ST['table1']}" if full else "Table 1"); rows = []; groups = []
    def add(head, var, cats):
        groups.append(len(rows)); rows.append([head, "", "", "", ""])
        for c in cats:
            r = T1(var, c)
            rows.append([LAB1[c], q1(r, "n", n0), q1(r, "pct_pond_amostra", f1), q1ci(r, "ia_total_pct", "ia_total_lo", "ia_total_hi", 1, "tab"), q1ci(r, "ia_grave_pct", "ia_grave_lo", "ia_grave_hi", 1, "tab")])
    rows.append(["All households", q1(tot, "n", n0), "100.0", q1ci(tot, "ia_total_pct", "ia_total_lo", "ia_total_hi", 1, "tab"), q1ci(tot, "ia_grave_pct", "ia_grave_lo", "ia_grave_hi", 1, "tab")])
    add("Race/colour", "Cor/raca", ["nao negra", "negra (preta+parda)"])
    if full:
        add("Sex (recorded)", "Sexo", ["homem", "mulher"])
        add("Education", "Instrucao", ["sem_fund", "fund_med", "medio_comp", "superior"])
    add("Per capita household income (minimum wages)", "Renda pc", ["q1", "q2", "q3", "q4", "q5"])
    if full:
        add("Residence", "Situacao", ["urbano", "rural"])
        cap = ("**Supplementary Table %s.** Households, weighted distribution and prevalence of food insecurity by every characteristic of the reference person, Continuous National Household Sample Survey (PNADC), fourth quarter of 2023. "
               "The condensed version, with race/colour and income only, is Table 1 of the article." % ST["table1"])
        bucket = "decl"
    else:
        cap = (f"**Table 1.** Households, weighted distribution and prevalence of food insecurity by race/colour of the reference person and per capita household income, Continuous National Household Sample Survey (PNADC), fourth quarter of 2023. "
               f"Education, recorded sex and residence are in Supplementary Table {ST['table1']}.")
        bucket = "captions"
    caption(d, cap, bucket)
    table(d, ["Characteristic", "Households (*n*)", "Weighted %", "Any insecurity, % (95% CI)", "Severe insecurity, % (95% CI)"], rows, widths=[5.4, 2.2, 2.0, 3.4, 3.4], group_rows=groups,
          note="Weighted percentages; 95% confidence intervals (CI) from replicate weights, on the logit scale. MW, minimum wage.")


def table_joint(d, tag, title, RA, RS, ses, ref_ses):
    setloc(tag); rows = []; groups = []
    cells = [("p00", "Reference: non-Black, " + ref_ses), ("p10", "Black, " + ref_ses), ("p01", "Non-Black, " + ses), ("p11", "Black, " + ses)]
    groups.append(len(rows)); rows.append(["Prevalence, % (households, *n*)", "", ""])
    for k, lab in cells:
        rows.append([f"{lab} (*n* = {q2(RA, 'n' + k[1:], n0)})", q2(RA, k, f1), q2(RS, k, f1)])
    groups.append(len(rows)); rows.append(["Prevalence ratio (95% CI); reference = 1", "", ""])
    rows.append(["Black, " + ref_ses, q2ci(RA, "rr10", "rr10_lo", "rr10_hi", 2, "tab"), q2ci(RS, "rr10", "rr10_lo", "rr10_hi", 2, "tab")])
    rows.append(["Non-Black, " + ses, q2ci(RA, "rr01", "rr01_lo", "rr01_hi", 2, "tab"), q2ci(RS, "rr01", "rr01_lo", "rr01_hi", 2, "tab")])
    rows.append(["Black, " + ses, q2ci(RA, "rr11", "rr11_lo", "rr11_hi", 2, "tab"), q2ci(RS, "rr11", "rr11_lo", "rr11_hi", 2, "tab")])
    groups.append(len(rows)); rows.append(["Interaction", "", ""])
    rows.append(["RERI, additive scale (95% CI)", q2ci(RA, "reri", "reri_lo_delta", "reri_hi_delta", 2, "tab"), q2ci(RS, "reri", "reri_lo_delta", "reri_hi_delta", 2, "tab")])
    rows.append(["RERI expected if joint effects were multiplicative", q2(RA, "reri_esperado_nulo_mult"), q2(RS, "reri_esperado_nulo_mult")])
    rows.append(["Ratio of PRs, multiplicative scale (95% CI)", q2ci(RA, "ror", "ror_lo", "ror_hi", 2, "tab"), q2ci(RS, "ror", "ror_lo", "ror_hi", 2, "tab")])
    groups.append(len(rows)); rows.append(["Decomposition of the joint prevalence difference (percentage points; arithmetic, not causal)", "", ""])
    rows.append(["Both disadvantages versus reference (95% CI)", qjdci(RA, 0).replace("95% CI ", ""), qjdci(RS, 0).replace("95% CI ", "")])
    rows.append(["   Component corresponding to race/colour alone", qjdci(RA, 1).replace("95% CI ", ""), qjdci(RS, 1).replace("95% CI ", "")])
    rows.append(["   Component corresponding to the socioeconomic disadvantage alone", qjdci(RA, 2).replace("95% CI ", ""), qjdci(RS, 2).replace("95% CI ", "")])
    rows.append(["   Interaction component (contrast)", qjdci(RA, 3).replace("95% CI ", ""), qjdci(RS, 3).replace("95% CI ", "")])
    rows.append(["   Interaction component, % of joint difference", qshare(RA), qshare(RS)])
    caption(d, f"**{tag}.** {title}: prevalence, prevalence ratios (PR) against a common reference, and interaction on the additive and multiplicative scales. Any and severe food insecurity, Continuous National Household Sample Survey (PNADC), fourth quarter of 2023.")
    table(d, ["Measure", "Any insecurity", "Severe insecurity"], rows, widths=[8.2, 3.9, 3.9], group_rows=groups,
          note="Crude, survey-weighted estimates (no covariates); percentage points for the decomposition. RERI, relative excess risk due to interaction, computed from prevalence ratios (PR); ratio of PRs = PR(both)/[PR(Black only) × PR(socioeconomic only)]; 95% confidence interval (CI) from 200 replicate weights. The interaction contrast equals RERI × reference prevalence. The decomposition is arithmetic and descriptive and does not identify causal effects; the interval for the interaction share is in Supplementary Table S16. MW, minimum wage.")


# ------------------------------------------------------------------ pagina de titulo e declaracoes
def title_page(d):
    p = d.add_paragraph(); r = p.add_run("TITLE PAGE"); r.bold = True; r.font.size = Pt(9)
    p = d.add_paragraph(); r = p.add_run(TITLE); r.bold = True; r.font.size = Pt(15)
    para(d, f"**Running head:** {RUNNING}", bucket="decl")
    para(d, "**Authors:** ⟦AUTHOR NAMES AND ORDER: to be completed⟧", bucket="decl")
    para(d, "**Affiliations:** ⟦to be completed⟧", bucket="decl")
    para(d, "**Corresponding author (marked with an asterisk in the author list):** ⟦name, postal address and e-mail address: to be completed⟧", bucket="decl")
    para(d, WORDINFO["text"], bucket="decl")
    d.add_page_break()


def declarations(d):
    H1(d, "Declarations")
    para(d, "**Ethics approval:** ⟦CONFIRM: name of the ethics committee and approval number, or the institutional statement that approval was not required and its reason. The study uses publicly available, anonymised secondary survey data; no approval, waiver or exemption is asserted here⟧", bucket="decl")
    para(d, "**Funding:** ⟦to be completed in the IJE format: 'This work was supported by …' with full funder names and grant numbers in brackets, or the applicable statement that there was no specific funding⟧", bucket="decl")
    para(d, "**Conflict of interest:** ⟦to be completed by all authors, in the form 'Conflict of Interest: None declared' only if true; the IJE conflict of interest form must also be submitted in the online system⟧", bucket="decl")
    para(d, "**Author contributions:** ⟦to be completed in detail for each author (CRediT roles); the guarantor of the paper must be named here⟧", bucket="decl")
    para(d, "**Data availability:** The survey microdata are public and available from IBGE (https://www.ibge.gov.br). The derived tables and the analysis and figure scripts are described in the Supplement. IJE requires all software code underlying the paper to be available: ⟦PENDING: repository, licence and DOI for the code and derived tables have not been created⟧.", bucket="decl")
    para(d, "**Supplementary data:** Supplementary data are available at *IJE* online.", bucket="decl")
    para(d, f"**AI tool use:** {AI_DECL}", bucket="decl")
    para(d, "**Acknowledgements:** ⟦to be completed⟧", bucket="decl")


def build_refs(d):
    H1(d, "References")
    for i, k in enumerate(ORDER, 1):
        p = d.add_paragraph(); rich(p, f"{i}. {ref_entry(k)}", size=10); p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.left_indent = Cm(0.9); p.paragraph_format.first_line_indent = Cm(-0.9); WC["refs"] += wcount(ref_entry(k))


# ------------------------------------------------------------------ main
def main():
    d = new_doc(line_numbers=True, spacing=2.0)
    title_page(d)
    p = d.add_paragraph(); r = p.add_run(TITLE); r.bold = True; r.font.size = Pt(14); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    bg, me, re_, co = abstract_parts()
    H1(d, "Abstract")
    for lab, txt in [("Background", bg), ("Methods", me), ("Results", re_), ("Conclusions", co)]:
        para(d, f"**{lab}:** {txt}", bucket="abstract")
    para(d, f"**Keywords:** {KEYWORDS}", bucket="keywords")
    H1(d, "Key Messages")
    for m in KEYMSG:
        p = d.add_paragraph(style="List Bullet"); p.add_run(m); WC["keymsg"] += wcount(m)
    H1(d, "Introduction"); intro(d)
    H1(d, "Methods"); methods(d)
    H1(d, "Results"); results(d)
    H1(d, "Discussion"); discussion(d); conclusion(d)
    declarations(d)
    build_refs(d)
    return d


if __name__ == "__main__":
    import montar_ije_saidas_20260925 as S
    S.run(main, globals())
