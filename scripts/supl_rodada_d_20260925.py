# -*- coding: utf-8 -*-
"""supl_rodada_d_20260925.py: tabelas suplementares S15-S20 (rodada D) do IJE, geradas SO' a partir das saidas auditadas em MANUSCRITO_IJE_20260925/rodada_D/.
Nenhuma estimativa nova; formatacao e traducao dos rotulos."""
import json
import pandas as pd
from ije_lib_20260925 import *     # noqa: F401,F403

RD = OUT / "rodada_D"
_J = lambda n: json.loads((RD / n).read_text(encoding="utf-8"))
PI, PE = "raca_x_renda(<=1/4 SM)", "raca_x_escolaridade(sem/fund. incompleto)"
LABQ = {"p00": "Prevalence, reference (%)", "p10": "Prevalence, race/colour only (%)", "p01": "Prevalence, income only (%)", "p11": "Prevalence, both (%)", "rr10": "PR, race/colour only", "rr01": "PR, income only",
        "rr11": "PR, both", "reri": "RERI", "reri_esperado": "RERI expected if multiplicative", "ror": "Ratio of PRs", "comp_raca_pp": "Component corresponding to race/colour alone (pp)",
        "comp_ses_pp": "Component corresponding to the socioeconomic disadvantage alone (pp)", "interacao_pp": "Interaction component (pp)", "conjunta_pp": "Joint difference (pp)", "participacao_pct": "Interaction share of the joint difference (%)"}
ORDQ = list(LABQ)
DECQ = lambda q: 1 if q in ("p00", "p10", "p01", "p11", "comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct") else 2
OUTC = {"ia_total": "Any", "ia_grave": "Severe"}
FM = {1: f1, 2: f2}
E = lambda e, lo, hi, d: f"{FM[d](e)} ({ci(lo, hi, d)})"


def add_rodada_d_tables(d, ST):
    conc = pd.read_csv(RD / "D4_concordancia_estimativas_e_ICs.csv"); d2 = pd.read_csv(RD / "D2_componentes_absolutos_IC.csv"); dg = pd.read_csv(RD / "D2_diagnostico_participacao.csv")
    s1 = pd.read_csv(RD / "D1_padronizado_vs_bruto_raca_renda.csv"); comp = pd.read_csv(RD / "D1_composicao_das_celulas.csv"); coef = pd.read_csv(RD / "D1_coeficientes_modelo_logistico.csv")
    d3 = pd.read_csv(RD / "D3_sensibilidade_corte_renda.csv"); d5 = pd.read_csv(RD / "D5_ignorados_comparacao_completa.csv"); sm5 = pd.read_csv(RD / "D5_maiores_diferencas_por_classe.csv")
    princ = _J("principal.json"); lon = _J("D9_estrato_solitario.json"); integ = _J("01_integridade_amostra.json"); chk = _J("01_checagens_pesos_replicados.json"); rcfg = _J("D4_R_survey_config_replicas.json")
    t8 = _J("D8_testes_integridade.json"); val = pd.read_csv(RD / "D4_validacao_python_vs_R.csv"); fl = pd.read_csv(RD / "01_fluxo_amostra_reproduzido.csv").set_index("etapa")["n"]; d5i = _J("D5_resumo.json")
    ABBR = "Abbreviations: PR, prevalence ratio; RERI, relative excess risk due to interaction; CI, confidence interval; pp, percentage points."

    # ---------------------------------------------------------------- S15a/b: variancia A, B, C
    for tag, pair, cap in (("a", PI, "race/colour × income (≤1/4 MW)"), ("b", PE, "race/colour × education (no schooling or incomplete primary)")):
        rows = []
        for q in ORDQ:
            row = [LABQ[q]]
            for y in ("ia_total", "ia_grave"):
                g = conc[(conc.par == pair) & (conc.desfecho == y) & (conc.quantidade == q)].iloc[0]; dd = DECQ(q)
                row += [FM[dd](g.A_est), ci(g.A_lo, g.A_hi, dd), ci(g.B_lo, g.B_hi, dd), ci(g.C_lo, g.C_hi, dd)]
            rows.append(row)
        caption(d, f"**Supplementary Table {ST['var']}{tag}.** {cap[0].upper() + cap[1:]}: point estimate and 95% CI under three variance methods. A, weights and primary sampling units (earlier configuration; linearization); B, weights and primary sampling units nested in strata (variable Estrato; linearization; a stratum with one unit centred at the overall mean); "
                   f"C, 200 replicate weights (Rao-Wu-Yue bootstrap; primary configuration). Crude estimates; the point estimate is the same under all three. {ABBR}", "decl")
        table(d, ["Quantity", "Any: estimate", "Any: CI, A", "Any: CI, B", "Any: CI, C", "Severe: estimate", "Severe: CI, A", "Severe: CI, B", "Severe: CI, C"], rows, font=7.5, bucket="decl")
    rows = [["Variance method A (PSU only)", "Earlier configuration; CI within 0.008% of the values first published for PRs, RERI and ratio of PRs"],
            ["Variance method B (PSU in strata)", f"Stratum {lon['estrato_com_1_UPA']} has one PSU ({lon['domicilios']} households, {lon['pct_do_peso_total']:.4f}% of the weight): policy 'adjust' (centred at the overall mean); policy 'certainty' (zero contribution) changes standard errors by at most {lon['politica_B_max_dif_rel_SE_pct_certainty_vs_adjust']:.4f}%"],
            ["Variance method C (replicate weights)", f"Columns V1028001-V1028200; type bootstrap; V = {rcfg['scale']:.9f} × sum of squared deviations of replicate estimates from the full-sample estimate (1/(R − 1), R = 200); functions recomputed in each replicate; no replication failures"],
            ["Agreement with R survey", f"B matches svydesign (maximum relative difference in standard errors {val[val.config == 'B'].dif_rel_se.max():.1e}); C matches withReplicates ({val[val.config == 'C2'].dif_rel_se.max():.1e}). The delta method on the replicate covariance (svycontrast) differs by up to {val[val.config == 'C'].dif_rel_se.max() * 100:.1f}% because it is a first-order approximation"],
            ["Choice of C", "Post-protocol amendment. The prespecified rule (agreement with R < 1e-6) was first evaluated against the delta method and failed, which by its literal reading would have selected B; C was adopted after identifying that the comparison used a different estimator. The decision is not presented as prespecified and was taken by the authors after inspecting all three sets of intervals. Conclusions do not depend on it: A, B and C give the same point estimates and similar intervals"],
            ["Replicate weights for the single-PSU stratum", "Not verified in a primary source how the replicates were generated for this stratum; in the data the weights of its PSU vary across replicates and enter the replicate variance"]]
    caption(d, f"**Supplementary Table {ST['var']}c.** Variance methods: definitions, validation and the post-protocol amendment.", "decl")
    table(d, ["Item", "Description"], rows, widths=[4.5, 11.5], font=8, bucket="decl")

    # ---------------------------------------------------------------- S16: componentes com IC
    rows = []
    for pair, nm in ((PI, "Race/colour × income"), (PE, "Race/colour × education")):
        for q in ("comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct"):
            row = [nm, LABQ[q]]
            for y in ("ia_total", "ia_grave"):
                g = d2[(d2.par == pair) & (d2.desfecho == y) & (d2.quantidade == q) & (d2.config == "C")].iloc[0]; row.append(E(g.estimativa, g.ic_inf, g.ic_sup, 1))
            rows.append(row)
    caption(d, f"**Supplementary Table {ST['comp']}a.** Absolute components of the decomposition of the joint prevalence difference, with 95% CI from replicate weights (configuration C). The decomposition is arithmetic and descriptive and does not identify causal effects. "
               "Intervals for the interaction share are shown for completeness; for any food insecurity in race/colour × income the share is small relative to its standard error and did not meet the stability rule set in the protocol (see part b), so it is not reported in the main text.", "decl")
    table(d, ["Contrast", "Component", "Any food insecurity", "Severe food insecurity"], rows, widths=[3.5, 6.5, 3.2, 3.2], font=8, bucket="decl")
    rows = [[{PI: "Race/colour × income", PE: "Race/colour × education"}[r["par"]], OUTC[r["desfecho"]], f1(r["conjunta_pp"]), f3(r["cv_conjunta"]), f1(r["participacao_pct"]), f"{f1(r['participacao_rep_min'])} to {f1(r['participacao_rep_max'])}",
             f"{r['fracao_replicas_|part|>3x|estimativa|'] * 100:.1f}%", "Yes" if r["regra_do_protocolo_permite_reportar_IC_da_participacao"] else "No"] for r in dg.to_dict("records")]
    caption(d, f"**Supplementary Table {ST['comp']}b.** Stability of the interaction share. Rule fixed in advance: report its interval only if the lower limit of the interval for the joint difference is above zero, its coefficient of variation is below 0.2 and no replicate share exceeds three times the estimate in absolute value. "
               "For any food insecurity in race/colour × income, 2% of replicates exceeded that bound although the denominator was stable; the rule was applied as written.", "decl")
    table(d, ["Contrast", "Outcome", "Joint difference (pp)", "CV of joint difference", "Share (%)", "Range of replicate shares (%)", "Replicates beyond 3× estimate", "Rule met"], rows, font=8, bucket="decl")

    # ---------------------------------------------------------------- S17: padronizada
    rows = []
    for q in ORDQ:
        row = [LABQ[q]]
        for y in ("ia_total", "ia_grave"):
            g = s1[(s1.desfecho == y) & (s1.quantidade == q)].iloc[0]; dd = DECQ(q); row += [E(g.bruto_est, g.bruto_lo, g.bruto_hi, dd), E(g.padronizado_est, g.padronizado_lo, g.padronizado_hi, dd), E(g.dif_padronizado_menos_bruto, g.dif_ic_inf, g.dif_ic_sup, dd)]
        rows.append(row)
    caption(d, f"**Supplementary Table {ST['std']}a.** Race/colour × income (≤1/4 MW): crude and standardized estimates, with 95% CI from replicate weights (the model is refitted in each replicate). Standardization (g-computation) averages, over all households, the probability predicted by a weighted logistic model with the joint category, recorded sex, education (four categories) and residence, with the joint category fixed. "
               "It describes the disparity if the four groups shared the sex, education and residence composition of the whole sample, assuming homogeneous covariate effects on the logit scale. It is a descriptive sensitivity analysis, not a causal effect, mediation or control of confounding, and does not replace the crude analysis. " + ABBR, "decl")
    table(d, ["Quantity", "Any: crude", "Any: standardized", "Any: difference", "Severe: crude", "Severe: standardized", "Severe: difference"], rows, font=7.5, bucket="decl")
    LC = {"nao negra, >1/4 SM (ref.)": "Non-Black, income >1/4 MW (reference)", "negra, >1/4 SM": "Black, income >1/4 MW", "nao negra, <=1/4 SM": "Non-Black, income ≤1/4 MW", "negra, <=1/4 SM": "Black, income ≤1/4 MW", "todos os domicilios (populacao-padrao)": "All households (standard population)"}
    rows = [[LC[r.celula], n0(r.n), f1(r.pct_mulher), f1(r.pct_rural), f1(r.pct_sem_fund_ou_menos), f1(r.pct_fund_med), f1(r.pct_medio_completo), f1(r.pct_superior)] for r in comp.itertuples()]
    caption(d, f"**Supplementary Table {ST['std']}b.** Composition of the four joint categories (weighted %), which motivated the covariates: recorded sex, education and residence differ markedly across the categories. Region, age and household composition were not included because there was no substantive justification set in advance.", "decl")
    table(d, ["Joint category", "Households (*n*)", "Women", "Rural", "No schooling or incomplete primary", "Complete primary or incomplete secondary", "Complete secondary", "Tertiary (complete or incomplete)"], rows, font=7.5, bucket="decl")
    LT = {"intercepto": "Intercept", "celula_10_so_raca": "Black, income >1/4 MW", "celula_01_so_renda": "Non-Black, income ≤1/4 MW", "celula_11_ambos": "Black, income ≤1/4 MW", "sexo_mulher": "Woman", "escol_fund_med": "Education: complete primary or incomplete secondary",
          "escol_medio_comp": "Education: complete secondary", "escol_superior": "Education: tertiary", "rural": "Rural residence"}
    rows = []
    for t in coef.termo.unique():
        row = [LT[t]]
        for y in ("ia_total", "ia_grave"):
            g = coef[(coef.desfecho == y) & (coef.termo == t)].iloc[0]; row.append(E(g.OR, g.OR_lo, g.OR_hi, 2))
        rows.append(row)
    caption(d, f"**Supplementary Table {ST['std']}c.** Weighted logistic model used for standardization: odds ratios (95% CI from replicate weights), not prevalence ratios. Reference: non-Black, income >1/4 MW, man, no schooling or incomplete primary, urban.", "decl")
    table(d, ["Term", "Any food insecurity (OR)", "Severe food insecurity (OR)"], rows, font=8, bucket="decl")

    # ---------------------------------------------------------------- S18: cortes
    CUTS = [("<=1/4 SM (primario)", "≤1/4 MW (primary)"), ("<=1/2 SM", "≤1/2 MW"), ("<=1 SM", "≤1 MW")]
    n3 = d3[(d3.config == "C") & (d3.quantidade == "p00") & (d3.desfecho == "ia_total")].set_index("corte")
    rows = [["Households (ref. / Black only / income only / both)"] + [f"{n0(n3.loc[c, 'n_ref'])} / {n0(n3.loc[c, 'n_so_raca'])} / {n0(n3.loc[c, 'n_so_renda'])} / {n0(n3.loc[c, 'n_ambos'])}" for c, _ in CUTS] * 2,
            ["Households below cut-point (weighted %)"] + [f1(n3.loc[c, "pct_baixa_renda_ponderado"]) for c, _ in CUTS] * 2]
    for q in ("p00", "p10", "p01", "p11", "rr10", "rr01", "rr11", "reri", "reri_esperado", "ror", "interacao_pp", "conjunta_pp", "participacao_pct"):
        row = [LABQ[q]]
        for y in ("ia_total", "ia_grave"):
            for c, _ in CUTS:
                g = d3[(d3.config == "C") & (d3.desfecho == y) & (d3.quantidade == q) & (d3.corte == c)].iloc[0]; row.append(E(g.estimativa, g.ic_inf, g.ic_sup, DECQ(q)))
        rows.append(row)
    caption(d, f"**Supplementary Table {ST['cut']}.** Exploratory sensitivity to the income cut-point: crude joint-category contrast between race/colour and per capita income at ≤1/4 MW (primary), ≤1/2 MW and ≤1 MW, with 95% CI from replicate weights. The primary cut-point was not changed and no cut-point is preferred. "
               "For severe insecurity the RERI is positive and the ratio of PRs below one at every cut-point; for any insecurity the RERI is compatible with zero at ≤1/4 and ≤1/2 MW but not at ≤1 MW. " + ABBR, "decl")
    table(d, ["Quantity"] + [f"{OUTC[y]}: {lab}" for y in ("ia_total", "ia_grave") for _, lab in CUTS], rows, font=7, bucket="decl")

    # ---------------------------------------------------------------- S19: ignorados
    LCL = {"prevalencia (geral e por categoria)": "Prevalence (overall and by category)", "prevalencia de celula": "Joint-category prevalence", "PR": "Prevalence ratio", "RERI": "RERI", "RERI esperado sob multiplicatividade": "RERI expected if multiplicative",
           "razao de PRs": "Ratio of PRs", "componente absoluto (pp)": "Absolute component (pp)", "participacao percentual da interacao": "Interaction share (percentage points)"}
    rows = []
    for y in ("ia_total", "ia_grave"):
        for q, lab, dd in (("p11", "Prevalence, both (%)", 1), ("rr11", "PR, both", 2), ("reri", "RERI", 2), ("ror", "Ratio of PRs", 2), ("interacao_pp", "Interaction component (pp)", 1)):
            g = d5[(d5.grupo == "quatro_celulas_bruto") & (d5.par == PI) & (d5.desfecho == y) & (d5.quantidade == q)].iloc[0]
            rows.append([OUTC[y], lab, E(g.principal_est, g.principal_lo, g.principal_hi, dd), E(g.excluidos_est, g.excluidos_lo, g.excluidos_hi, dd), f"{g.dif_abs:+.3f}".replace("-", "−")])
        g = d5[(d5.grupo == "prevalencia") & d5.par.str.startswith("renda q5") & (d5.desfecho == y)].iloc[0]
        rows.append([OUTC[y], "Prevalence, income >2 MW (%; contains the 77 households with ignored income)", E(g.principal_est, g.principal_lo, g.principal_hi, 2), E(g.excluidos_est, g.excluidos_lo, g.excluidos_hi, 2), f"{g.dif_abs:+.3f}".replace("-", "−")])
    caption(d, f"**Supplementary Table {ST['ign']}a.** Race/colour × income: primary analysis (n = {n0(d5i['n_total'])}) and after excluding the {d5i['n_raca_ignorada']} households with ignored race/colour and the {d5i['n_renda_ignorada']} with ignored income (n = {n0(d5i['n_analise_restrita'])}). "
               "The original coding, which classifies them as non-Black and as income >2 MW, is kept only to reproduce the primary analysis and is not a substantive choice. The joint-category estimates are stable; the prevalence in the >2 MW band changes by 0.06 percentage points for any insecurity. A difference in the last printed digit (for example RERI 1.28 versus 1.29) reflects rounding of a difference below 0.005. 95% CI from replicate weights.", "decl")
    table(d, ["Outcome", "Quantity", "Primary analysis", "Excluding ignored records", "Difference"], rows, font=8, bucket="decl")
    rows = [[{"bruta": "Crude", "padronizada": "Standardized"}[r.analise], LCL[r.classe], f"{abs(r.maior_dif_abs):.4f}", r.unidade.replace("razao/indice", "ratio or index"), f"{r.maior_dif_sobre_meia_largura_IC:.3f}"] for r in sm5.itertuples()]
    caption(d, f"**Supplementary Table {ST['ign']}b.** Largest absolute difference between the primary analysis and the analysis excluding ignored records, by class of estimand (both outcomes; race/colour × income and × education for crude, race/colour × income for standardized), and the ratio of that difference to the half-width of the interval of the primary analysis. "
               "The pre-specified criterion (below 0.10) was met in every class except the prevalence by category, driven by the >2 MW band in Table 1.", "decl")
    table(d, ["Analysis", "Class of estimand", "Largest absolute difference", "Unit", "Difference / half-width of CI"], rows, font=8, bucket="decl")

    # ---------------------------------------------------------------- S20: amostra e desenho
    R_ = lambda x: n0(x)
    rows = [["Person records in the file", R_(integ["linhas_pessoas"])], ["Reference persons (V2005 = 01) = analytic households", R_(integ["n_linhas_V2005_01"])],
            ["Households with exactly one reference person (none; two or more)", f"{R_(integ['dom_com_1_responsavel'])} ({integ['dom_com_0_responsavel']}; {integ['dom_com_2mais_responsaveis']})"],
            ["Reference persons with valid EBIA (SD17001 1-4) and positive weight", f"{R_(fl['Pessoas de referencia com SD17001 em 1-4'])}; no household excluded"],
            ["Official household key (UPA + V1008 + V1014) unique; earlier reconstructed identifier equivalent", f"{R_(integ['n_chaves_oficiais_UPA_V1008_V1014'])}; {'yes' if integ['id_reconstruido_equivale_a_chave_oficial'] else 'no'}"],
            ["Primary sampling units; strata (variable Estrato, positions 21-27); strata with one PSU", f"{R_(fl['UPAs distintas'])}; {R_(fl['Estratos distintos (variavel oficial Estrato)'])}; {fl['Estratos com uma unica UPA']}"],
            ["Final weight V1028 (15 characters); replicate weights", f"V1028; V1028001-V1028200 ({chk['n_colunas']} columns, {chk['faltantes']} missing, {chk['colunas_todas_zero']} all-zero, {chk['colunas_identicas_ao_peso_final']} equal to the final weight)"],
            ["Race/colour ignored (code 9), coded non-Black; income ignored (code 9), coded >2 MW", f"{d5i['n_raca_ignorada']}; {d5i['n_renda_ignorada']} (see Supplementary Table {ST['ign']})"],
            ["Automated integrity tests; simulated corruptions detected", f"{sum(1 for r in t8['testes'] if r['resultado'] == 'PASS')} of {len(t8['testes'])} pass; {sum(1 for a in t8['autoteste_mutacao'] if a['falhou_como_esperado'])} of {len(t8['autoteste_mutacao'])} detected"]]
    caption(d, f"**Supplementary Table {ST['samp']}.** Sample flow, design variables and integrity checks (fourth quarter of 2023 microdata; layout and dictionary from the Brazilian Institute of Geography and Statistics). The comparison of weighted totals with the institute's published table 9554 (0.25% to 0.57% lower in the microdata) is an internal control, not an external validation.", "decl")
    table(d, ["Item", "Result"], rows, widths=[9.5, 6.5], font=8, bucket="decl")
