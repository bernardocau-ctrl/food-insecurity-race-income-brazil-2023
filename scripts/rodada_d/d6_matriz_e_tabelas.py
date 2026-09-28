# -*- coding: utf-8 -*-
"""
d6_matriz_e_tabelas.py
(D) matriz "resultado original vs resultado corrigido" (CSV) e tabelas formatadas PROPOSTAS para o suplemento (.docx).
Nao toca no manuscrito. Original = dados/v2_20260925 (t1, t2); corrigido = configuracao principal (principal.json), com A e B como sensibilidade.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *

PRINC = json.loads((OUTD / "principal.json").read_text(encoding="utf-8"))["principal"]
conc = pd.read_csv(OUTD / "D4_concordancia_estimativas_e_ICs.csv")
NULL = {"rr10": 1, "rr01": 1, "rr11": 1, "ror": 1, "reri": 0, "reri_esperado": None, "comp_raca_pp": 0, "comp_ses_pp": 0, "interacao_pp": 0, "conjunta_pp": 0, "participacao_pct": 0, "prevalencia_pct": None, "p00": None, "p10": None, "p01": None, "p11": None}
d2 = pd.read_csv(OUTD / "D2_componentes_absolutos_IC.csv")
rows = []
for _, r in conc.iterrows():
    q = r["quantidade"]; nul = NULL.get(q)
    orig_ci = not np.isnan(r.get("pub_lo", np.nan)) if "pub_lo" in r.index else False
    o_est = r["pub_est"] if "pub_est" in r.index and not np.isnan(r["pub_est"]) else np.nan
    row = {"grupo": r.grupo, "par": r.par, "desfecho": r.desfecho, "quantidade": q,
           "original_est": o_est, "original_ic_inf": r.get("pub_lo", np.nan), "original_ic_sup": r.get("pub_hi", np.nan),
           "config_A_replicada_est": r.A_est, "config_A_ic_inf": r.A_lo, "config_A_ic_sup": r.A_hi,
           "B_est": r.B_est, "B_ic_inf": r.B_lo, "B_ic_sup": r.B_hi, "C_est": r.C_est, "C_ic_inf": r.C_lo, "C_ic_sup": r.C_hi}
    P = {"A": (r.A_lo, r.A_hi), "B": (r.B_lo, r.B_hi), "C": (r.C_lo, r.C_hi)}[PRINC]
    row["corrigido_config"] = PRINC; row["corrigido_est"] = {"A": r.A_est, "B": r.B_est, "C": r.C_est}[PRINC]; row["corrigido_ic_inf"], row["corrigido_ic_sup"] = P
    row["dif_est_corrigido_menos_original"] = row["corrigido_est"] - o_est if not np.isnan(o_est) else np.nan
    if orig_ci:
        row["dif_abs_ic_inf"] = P[0] - r["pub_lo"]; row["dif_abs_ic_sup"] = P[1] - r["pub_hi"]
        row["dif_rel_ic_inf_pct"] = (P[0] / r["pub_lo"] - 1) * 100 if r["pub_lo"] else np.nan; row["dif_rel_ic_sup_pct"] = (P[1] / r["pub_hi"] - 1) * 100 if r["pub_hi"] else np.nan
        row["razao_largura_corrigido_sobre_original"] = (P[1] - P[0]) / (r["pub_hi"] - r["pub_lo"])
    if nul is not None:
        exc_c = not (P[0] <= nul <= P[1]); row["exclui_nulo_corrigido"] = exc_c
        if orig_ci:
            exc_o = not (r["pub_lo"] <= nul <= r["pub_hi"]); row["exclui_nulo_original"] = exc_o
            row["mudanca_de_interpretacao"] = "SIM" if exc_o != exc_c else "nao"
        else: row["mudanca_de_interpretacao"] = "IC novo (nao havia IC original)"
    else: row["mudanca_de_interpretacao"] = "n/a (sem valor nulo)"
    rows.append(row)
M = pd.DataFrame(rows)
# componentes e participacao para o par raca x renda: sem IC original
M.to_csv(OUTD / "D_matriz_original_vs_corrigido.csv", index=False, encoding="utf-8-sig")
ch = M[M.mudanca_de_interpretacao == "SIM"]
resumo = {"linhas": len(M), "mudancas_de_interpretacao_pelo_criterio_IC_exclui_nulo": int(len(ch)), "config_corrigida": PRINC,
          "max_dif_abs_estimativa_pontual": float(M["dif_est_corrigido_menos_original"].abs().max()),
          "dif_rel_IC_maxima_pct_(PRs_RERI_razao)": float(M[M.quantidade.isin(["rr10", "rr01", "rr11", "reri", "ror"])][["dif_rel_ic_inf_pct", "dif_rel_ic_sup_pct"]].abs().max().max()),
          "razao_largura_min_max": [float(M["razao_largura_corrigido_sobre_original"].min()), float(M["razao_largura_corrigido_sobre_original"].max())]}
(OUTD / "D_matriz_resumo.json").write_text(json.dumps(resumo, indent=1), encoding="utf-8"); print(json.dumps(resumo, indent=1)); print(ch[["par", "desfecho", "quantidade"]].to_string())

# ---------------------------------------------------------------- tabelas formatadas (docx)
doc = Document(); st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(9)
sec = doc.sections[0]; sec.orientation = 1; sec.page_width, sec.page_height = sec.page_height, sec.page_width
for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"): setattr(sec, m, Cm(1.8))


def rules(t):
    tblPr = t._tbl.tblPr; b = OxmlElement("w:tblBorders")
    for edge, val in (("top", "single"), ("left", "nil"), ("bottom", "single"), ("right", "nil"), ("insideH", "nil"), ("insideV", "nil")):
        el = OxmlElement(f"w:{edge}"); el.set(qn("w:val"), val)
        if val == "single": el.set(qn("w:sz"), "8"); el.set(qn("w:color"), "000000")
        b.append(el)
    tblPr.append(b)


def tab(title, header, body, note="", widths=None):
    p = doc.add_paragraph(); r = p.add_run(title); r.bold = True
    t = doc.add_table(rows=1, cols=len(header)); rules(t)
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; rr = c.paragraphs[0].add_run(h); rr.bold = True; rr.font.size = Pt(8.5)
    for row in body:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; rr = cells[i].paragraphs[0].add_run(str(v)); rr.font.size = Pt(8.5)
            if i > 0: cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if note: p = doc.add_paragraph(); rr = p.add_run(note); rr.font.size = Pt(8)
    doc.add_paragraph()


NB = " "
def f(x, d=2):
    if x is None or (isinstance(x, float) and np.isnan(x)): return ""
    s = f"{x:.{d}f}"; return s.replace("-", "−")
def ci(e, lo, hi, d=2): return f"{f(e, d)} ({f(lo, d)} a {f(hi, d)})" if lo < 0 else f"{f(e, d)} ({f(lo, d)}-{f(hi, d)})"
def ci2(lo, hi, d=2): return f"{f(lo, d)} a {f(hi, d)}" if lo < 0 else f"{f(lo, d)}-{f(hi, d)}"
LAB = {"p00": "Prevalência, referência (%)", "p10": "Prevalência, só raça/cor (%)", "p01": "Prevalência, só renda (%)", "p11": "Prevalência, ambos (%)", "rr10": "PR, só raça/cor", "rr01": "PR, só renda", "rr11": "PR, ambos",
       "reri": "RERI", "reri_esperado": "RERI esperado se multiplicativo", "ror": "Razão de PRs", "comp_raca_pp": "Componente correspondente à raça/cor isolada (pp)", "comp_ses_pp": "Componente correspondente à renda isolada (pp)",
       "interacao_pp": "Componente de interação (pp)", "conjunta_pp": "Diferença conjunta (pp)", "participacao_pct": "Participação da interação na diferença conjunta (%)"}
ORDER = ["p00", "p10", "p01", "p11", "rr10", "rr01", "rr11", "reri", "reri_esperado", "ror", "comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct"]
OUTL = {"ia_total": "Qualquer insegurança", "ia_grave": "Insegurança grave"}
p = doc.add_paragraph(); r = p.add_run("Tabelas PROPOSTAS para o suplemento (rodada D, 25/09/2026). NÃO aplicadas ao manuscrito. Identificadores 'R-D…' vinculam cada tabela ao CSV de origem em rodada_D/. Cálculos sem arredondar; arredondamento só na apresentação."); r.italic = True
for pair, tag, cap in (("raca_x_renda(<=1/4 SM)", "R-D4a", "Raça/cor × renda per capita (≤1/4 vs >1/4 SM)"), ("raca_x_escolaridade(sem/fund. incompleto)", "R-D4b", "Raça/cor × escolaridade (sem instrução ou fundamental incompleto vs mais)")):
    body = []
    for q in ORDER:
        row = [LAB[q]]
        for y in ("ia_total", "ia_grave"):
            g = conc[(conc.par == pair) & (conc.desfecho == y) & (conc.quantidade == q)].iloc[0]
            dd = 1 if q in ("p00", "p10", "p01", "p11", "comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct") else 2
            row += [f(g.A_est, dd), ci2(g.A_lo, g.A_hi, dd), ci2(g.B_lo, g.B_hi, dd), ci2(g.C_lo, g.C_hi, dd)]
        body.append(row)
    tab(f"Tabela {tag}. {cap}: estimativa e IC de 95% sob três configurações de variância (fonte: D4_estimativas_por_configuracao.csv)",
        ["Quantidade"] + [f"{o}: {c}" for o in ("Qualquer", "Grave") for c in ("estimativa", "IC A: pesos+UPA", "IC B: +Estrato", "IC C: pesos replicados")], body,
        "A estimativa pontual é idêntica nas três configurações (mesmos pesos V1028). A: linearização com UPA (configuração antiga). B: linearização com UPA em Estrato. C: 200 pesos replicados (bootstrap de Rao, Wu e Yue), configuração principal. PR, razão de prevalências; RERI, excesso de risco relativo devido à interação; pp, pontos percentuais.")
# prevalencias
body = []
for lab in conc[conc.grupo == "prevalencia"].par.unique():
    row = [lab]
    for y in ("ia_total", "ia_grave"):
        g = conc[(conc.grupo == "prevalencia") & (conc.par == lab) & (conc.desfecho == y)].iloc[0]
        row += [f(g.A_est, 1), ci2(g.A_lo, g.A_hi, 1), ci2(g.B_lo, g.B_hi, 1), ci2(g.C_lo, g.C_hi, 1)]
    body.append(row)
tab("Tabela R-D4c. Prevalências (%) das categorias da Tabela 1 sob três configurações de variância (IC na escala logit)", ["Categoria"] + [f"{o}: {c}" for o in ("Qualquer", "Grave") for c in ("prevalência", "IC A", "IC B", "IC C")], body,
    "'renda q5' inclui os 77 domicílios com faixa de renda ignorada (código original).")
# D-2
body = []
for pair in ("raca_x_renda(<=1/4 SM)", "raca_x_escolaridade(sem/fund. incompleto)"):
    for q in ["comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct"]:
        row = [pair.split("(")[0].replace("_", " "), LAB[q]]
        for y in ("ia_total", "ia_grave"):
            g = d2[(d2.par == pair) & (d2.desfecho == y) & (d2.quantidade == q) & (d2.config == PRINC)].iloc[0]; row.append(ci(g.estimativa, g.ic_inf, g.ic_sup, 1))
        body.append(row)
tab("Tabela R-D2. Componentes absolutos da decomposição com IC de 95% (configuração principal C; fonte: D2_componentes_absolutos_IC.csv)", ["Contraste", "Componente", "Qualquer insegurança", "Insegurança grave"], body,
    "Decomposição aritmética e descritiva; não identifica efeitos causais. A participação percentual tem IC estável para a insegurança grave nos dois contrastes e para qualquer insegurança em raça × escolaridade; para qualquer insegurança em raça × renda, o IC da participação não satisfaz a regra de estabilidade do protocolo (ver relatório).")
# D-1
s = pd.read_csv(OUTD / "D1_padronizado_vs_bruto_raca_renda.csv"); body = []
for q in ORDER:
    row = [LAB[q]]
    for y in ("ia_total", "ia_grave"):
        g = s[(s.desfecho == y) & (s.quantidade == q)].iloc[0]; dd = 1 if q in ("p00", "p10", "p01", "p11", "comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct") else 2
        row += [ci(g.bruto_est, g.bruto_lo, g.bruto_hi, dd), ci(g.padronizado_est, g.padronizado_lo, g.padronizado_hi, dd)]
    body.append(row)
tab("Tabela R-D1. Raça/cor × renda (≤1/4 SM): análise bruta e padronizada por sexo registrado, escolaridade e residência (fonte: D1_padronizado_vs_bruto_raca_renda.csv)", ["Quantidade", "Qualquer: bruta", "Qualquer: padronizada", "Grave: bruta", "Grave: padronizada"], body,
    "Padronização (g-computation): prevalência em cada célula prevista por regressão logística ponderada (células + sexo registrado + escolaridade em 4 categorias + residência) e promediada, com pesos, sobre todos os domicílios. IC pelos 200 pesos replicados (modelo reajustado em cada réplica). Análise descritiva e secundária; não é efeito causal, mediação nem eliminação de confusão; supõe efeitos das covariáveis homogêneos na escala logit.")
# D-3
t3 = pd.read_csv(OUTD / "D3_sensibilidade_corte_renda.csv"); t3 = t3[t3.principal]; body = []
for q in ["p00", "p10", "p01", "p11", "rr10", "rr01", "rr11", "reri", "reri_esperado", "ror", "interacao_pp", "conjunta_pp"]:
    row = [LAB[q]]
    for y in ("ia_total", "ia_grave"):
        for cut in ("<=1/4 SM (primario)", "<=1/2 SM", "<=1 SM"):
            g = t3[(t3.desfecho == y) & (t3.quantidade == q) & (t3.corte == cut)].iloc[0]; dd = 1 if q in ("p00", "p10", "p01", "p11", "interacao_pp", "conjunta_pp") else 2
            row.append(ci(g.estimativa, g.ic_inf, g.ic_sup, dd))
    body.append(row)
n = t3[(t3.desfecho == "ia_total") & (t3.quantidade == "p00")].set_index("corte")
body.insert(0, ["n (ref / só raça / só renda / ambos)"] + [f"{int(n.loc[c,'n_ref'])} / {int(n.loc[c,'n_so_raca'])} / {int(n.loc[c,'n_so_renda'])} / {int(n.loc[c,'n_ambos'])}" for c in ("<=1/4 SM (primario)", "<=1/2 SM", "<=1 SM")] * 2)
tab("Tabela R-D3. Sensibilidade ao ponto de corte de renda (EXPLORATÓRIA); contraste bruto raça/cor × renda per capita (fonte: D3_sensibilidade_corte_renda.csv)", ["Quantidade"] + [f"{o}: {c}" for o in ("Qualquer", "Grave") for c in ("≤1/4 SM (primário)", "≤1/2 SM", "≤1 SM")], body,
    "Análise exploratória de robustez; o corte primário permanece ≤1/4 SM e nenhum corte foi escolhido como preferido. IC pela configuração principal (C).")
# D-5
sm = pd.read_csv(OUTD / "D5_maiores_diferencas_por_classe.csv"); body = [[r.analise, r.classe, f(r.maior_dif_abs, 4), r.unidade, f(r.maior_dif_relativa_pct, 2) + "%", f(r.maior_dif_sobre_meia_largura_IC, 3), r.onde_maior_dif_abs] for r in sm.itertuples()]
tab("Tabela R-D5. Exclusão dos domicílios com raça/cor ignorada (19) e renda ignorada (77): maior diferença absoluta por classe de estimando (fonte: D5_maiores_diferencas_por_classe.csv)", ["Análise", "Classe", "Maior dif. abs.", "Unidade", "Maior dif. relativa", "Maior dif. / meia-largura do IC", "Onde"], body,
    "Comparação com a análise principal (n = 173.676). Amostra restrita n = 173.580.")
doc.save(OUTD / "E_tabelas_suplementares_propostas_rodadaD.docx")
log_execucao("d6_matriz_e_tabelas.py", resumo)
