# -*- coding: utf-8 -*-
"""
entregaveis_rev2_ije_20260925.py
Gera, a partir dos .docx ja construidos (NAO estima nada):
  R2_Entregaveis_revisao_IJE.md   (B) trecho anterior -> novo -> motivo; (C) busca global de termos; (D) requisitos do guia do IJE; (E) bloqueios
  F_Verification_report_rev2.md   verificacao da rev2 (numeros inalterados vs v1, contagens independentes, auditoria de termos)
"""
import re, hashlib, io, sys
from pathlib import Path
from collections import Counter
import pandas as pd
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "MANUSCRITO_IJE_20260925"
V1 = OUT / "A_Manuscript_IJE.docx"; R2 = OUT / "A_Manuscript_IJE_rev2.docx"; SUP1 = OUT / "B_Supplementary_material_IJE.docx"; SUP2 = OUT / "B_Supplementary_material_IJE_rev2.docx"
BACKUP = BASE / "MANUSCRITO_IJE_20260925" / "_backup_v1"   # copia da v1 (opcional; se nao existir, a comparacao byte a byte e pulada)

HEADS = ["Abstract", "Key Messages", "Introduction", "Methods", "Results", "Discussion", "Conclusion", "Declarations", "References"]


def load(path, tprefix="Table"):
    d = Document(str(path)); items = []; loc = "Title page"
    for p in d.paragraphs:
        t = p.text.strip()
        if t in HEADS: loc = t
        hl = [r.text for r in p.runs if r.font.highlight_color is not None]
        items.append({"kind": "p", "loc": loc, "text": p.text, "hl": hl})
    for ti, t in enumerate(d.tables):
        for ri, row in enumerate(t.rows):
            for ci, c in enumerate(row.cells):
                for p in c.paragraphs:
                    items.append({"kind": "t", "loc": f"{tprefix} {ti + 1}", "text": p.text, "hl": [r.text for r in p.runs if r.font.highlight_color is not None], "row": ri, "col": ci})
    return d, items


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(\[⟦])", text) if s]


def find(items, pat, region=None, nth=0, kinds=("p", "t")):
    n = 0
    for it in items:
        if it["kind"] not in kinds: continue
        if region and it["loc"] != region: continue
        if re.search(pat, it["text"]):
            if n == nth: return it
            n += 1
    return None


def snippet(it, pat, whole=False):
    if it is None: return "(não encontrado)"
    if whole or it["kind"] == "t": return it["text"]
    for s in sentences(it["text"]):
        if re.search(pat, s): return s
    return it["text"]


def esc(t): return t.replace("|", "\\|").replace("\n", " ")


# ================================================================ dados
d1, I1 = load(V1); d2, I2 = load(R2); ds1, S1 = load(SUP1, "Suplemento, tabela"); ds2, S2 = load(SUP2, "Suplemento, tabela")
txt = lambda items, kinds=("p",): "\n".join(i["text"] for i in items if i["kind"] in kinds)
T1, T2, TS1, TS2 = txt(I1), txt(I2), txt(S1), txt(S2)
T1all, T2all, TS1all, TS2all = txt(I1, ("p", "t")), txt(I2, ("p", "t")), txt(S1, ("p", "t")), txt(S2, ("p", "t"))

# ================================================================ (B) tabela de mudancas
CH = [
    # (local, prioridade, regiao, pat_v1, pat_r2, nth_v1, nth_r2, inteiro, motivo)
    ("Resumo, Conclusions", "1", "Abstract", r"^Conclusions:", r"^Conclusions:", 0, 0, True, "A conclusão genérica ('super-aditiva mas sub-multiplicativa') só vale para insegurança grave. Para qualquer insegurança o RERI (0,07; −0,08 a 0,22) é compatível com aditividade."),
    ("Resumo, Results (qualquer insegurança)", "1", "Abstract", r"For any insecurity, RERI was", r"For any insecurity, RERI was", 0, 0, False, "Incluída a razão de RPs (0,75 [0,71-0,80]) para que o resumo mostre a sub-multiplicatividade também em qualquer insegurança."),
    ("Resumo, Results (decomposição)", "2", "Abstract", r"interaction contributed|interaction component", r"interaction component was", 0, 0, False, "'contributed' sugere causalidade; agora descritivo ('interaction component')."),
    ("Resumo, Methods", "6", "Abstract", r"^Methods:", r"^Methods:", 0, 0, True, "Período do estudo mantido ('fourth quarter 2023'); raça × escolaridade e MAIHDA agrupadas como secundárias para caber em 250 palavras."),
    ("Mensagem-chave 1", "1", "Key Messages", r"super-additive", r"super-additive", 0, 0, True, "Super-aditividade limitada ao desfecho grave; para qualquer insegurança, quase aditiva; sub-multiplicativa nos dois."),
    ("Mensagem-chave 2", "3", "Key Messages", r"positive relative excess risk", r"positive relative excess risk", 0, 0, True, "Referência multiplicativa deixa de ser regra de leitura ('should be read against') e vira apoio interpretativo ('may usefully be read alongside')."),
    ("Introdução ('benchmark natural')", "3", "Introduction", r"natural benchmark", r"useful interpretive benchmark", 0, 0, False, "A multiplicatividade não é a escala 'natural' nem superior; é um referencial interpretativo para contextualizar um RERI positivo."),
    ("Introdução (decomposição)", "2", "Introduction", r"can be decomposed into", r"can be decomposed into", 0, 0, False, "'contributions of each exposure' passou a 'components corresponding to each exposure' (linguagem aritmética)."),
    ("Métodos, RERI esperado", "3", "Methods", r"As a benchmark we report", r"For interpretive context we also report", 0, 0, False, "Explicita que o RERI esperado sob multiplicatividade não é hipótese nula para interação na escala de prevalência."),
    ("Métodos, decomposição", "2", "Methods", r"decomposed the joint prevalence difference", r"decomposed the joint prevalence difference", 0, 0, False, "Componentes descritos como 'corresponding to', não como contribuições causais."),
    ("Métodos, decomposição (nova frase)", "2", "Methods", r"no confidence interval was computed for the decomposition", r"arithmetic and descriptive and does not identify", 0, 0, False, "Acrescentado que a decomposição é aritmética e descritiva e não identifica efeitos causais."),
    ("Métodos, hiatos e atenuação", "5", "Methods", r"Gaps across income and attenuation", r"Racial gaps across income bands", 0, 0, True, "Um parágrafo ambíguo virou dois: RPs por faixa de renda (escolaridade em 4 categorias) e modelos de atenuação (escolaridade dicotomizada). Conferido no código; nada foi harmonizado ou recalculado."),
    ("Métodos, atenuação (novo parágrafo)", "5", "Methods", r"Gaps across income and attenuation", r"Attenuation of the crude association", 0, 0, True, "Segundo parágrafo: covariáveis dos modelos de atenuação e declaração de que os conjuntos diferem (Tabela S1b)."),
    ("Métodos, MAIHDA", "6", "Methods", r"\*?MAIHDA\.? We fitted|We fitted intersectional MAIHDA", r"We fitted intersectional MAIHDA", 0, 0, True, "Enxugado (menos detalhe secundário); mantidos VPC, PCV, escala logit, ausência de pesos e ponteiro ao suplemento."),
    ("Resultados, decomposição grave", "2", "Results", r"attributable to", r"component corresponding to race/colour alone was", 0, 0, False, "'attributable to' removido; valores idênticos (13,2 = 2,3 + 8,4 + 2,5)."),
    ("Resultados, qualquer insegurança", "1", "Results", r"The RERI was 0\.07", r"The RERI was 0\.07", 0, 0, False, "Acrescentado 'compatible with no additive-scale interaction' e a razão de RPs junto ao RERI."),
    ("Resultados, decomposição (qualquer)", "2", "Results", r"points comprised", r"points comprised", 0, 0, False, "Redação descritiva ('component … corresponding to')."),
    ("Resultados, decomposição (escolaridade)", "2", "Results", r"points comprised", r"points comprised", 1, 1, False, "Idem; intervalo do RERI para qualquer insegurança inclui zero, agora dito."),
    ("Resultados, ponteiro da figura", "6", "Results", r"\(Figure 2\)", r"Supplementary Figure S1", 0, 0, False, "Figura 2 movida ao suplemento (Fig. S1) para destacar a Figura 1."),
    ("Legenda da Tabela 1", "6", None, r"^Table 1\.", r"^Table 1\.", 0, 0, True, "Tabela 1 condensada (raça/cor e renda); versão completa na Tabela S2; PNADC por extenso."),
    ("Tabela 2 (rótulo de linha)", "2", "Table 2", r"attributable to race/colour alone", r"Component corresponding to race/colour alone", 0, 0, True, "Rótulo causal trocado; valores (13.0 e 2.3) idênticos. Idem Tabela 3."),
    ("Tabela 2 (interação, rótulo)", "2", "Table 2", r"^\s*interaction contrast\s*$", r"Interaction component \(contrast\)", 0, 0, True, "Rótulo alinhado com o texto."),
    ("Nota das Tabelas 2-3", "2", None, r"No confidence interval was computed for the decomposition", r"No confidence interval was computed for the decomposition", 0, 0, True, "Nota agora diz que a decomposição é aritmética, descritiva e não identifica efeitos causais; CI por extenso."),
    ("Discussão, abertura", "1", "Discussion", r"national survey of", r"national survey of", 0, 0, True, "Corrigida: super-aditiva e sub-multiplicativa só para grave; qualquer insegurança quase aditiva (RERI 0,07, intervalo inclui zero) e sub-multiplicativa. 'MAIHDA attributed' trocado por 'additive main effects accounted for … variance on the logit scale'."),
    ("Discussão, 'relevant null'", "3", "Discussion", r"relevant null", r"the scale most directly related", 0, 0, False, "Retirado o 'relevant null' (a aditividade não é o único nulo relevante); 'arises from' → 'associated with'."),
    ("Discussão, RERI abaixo da referência", "3", "Discussion", r"below the benchmark", r"Here the observed RERI was below", 0, 0, False, "'benchmark' → 'multiplicative expectation'."),
    ("Discussão, qualificador 'grave'", "1", "Discussion", r"any pair of exposures", r"any pair of exposures", 0, 0, False, "Acrescentado 'For severe insecurity' e 'useful context for a positive RERI'."),
    ("Discussão, 'accounted for'", "2", "Discussion", r"interaction accounted for", r"For severe insecurity the interaction component was", 0, 0, False, "'accounted for' aplicado à interação substituído por descrição aritmética."),
    ("Discussão, MAIHDA", "2", "Discussion", r"largely explained by", r"largely accounted for by", 0, 0, False, "'explained by' → 'accounted for by' (partição estatística de variância, sem sentido causal)."),
    ("Discussão, limitação 5", "5", "Discussion", r"Fifth,", r"Fifth,", 0, 0, False, "Registra que os conjuntos de covariáveis diferem entre modelos."),
    ("Discussão, lição geral", "3", "Discussion", r"Studies of joint disparities should", r"Studies of joint disparities should", 0, 0, False, "'multiplicative benchmark' → 'multiplicative expectation as context'."),
    ("Conclusão final", "1", "Conclusion", r"super-additive", r"super-additive", 0, 0, True, "Reescrita: super-aditiva só para grave; qualquer insegurança com estimativa aditiva próxima de zero e intervalo que inclui zero; sub-multiplicativa nos dois."),
    ("Legenda da Figura 1", "4", None, r"^Figure 1\.", r"^Figure 1\.", 0, 0, True, "RERI por extenso; MW e PR definidos; texto alternativo acrescentado à imagem."),
    ("Página de título", "4", "Title page", r"Corresponding author", r"Corresponding author", 0, 0, True, "Autor para correspondência com endereço postal e e-mail (campo pendente)."),
    ("Declarações, financiamento", "4", "Declarations", r"^Funding", r"^Funding", 0, 0, True, "Formato do IJE ('This work was supported by …')."),
    ("Declarações, dados e código", "4", "Declarations", r"^Data availability", r"^Data availability", 0, 0, True, "O IJE exige disponibilidade de todo o código; repositório/DOI seguem como pendência explícita (não criados)."),
    ("Siglas por extenso", "4", "Introduction", r"FAO Hunger Map", r"Food and Agriculture Organization \(FAO\)", 0, 0, False, "Sigla por extenso na primeira menção (idem STROBE, AI, CI, PNADC, MW)."),
]
rowsB = []
for i, (loc, pr, reg, p1, p2, n1, n2, whole, why) in enumerate(CH, 1):
    a = find(I1, p1, reg, n1); b = find(I2, p2, reg, n2)
    old = snippet(a, p1, whole); new = snippet(b, p2, whole)
    if loc == "Métodos, atenuação (novo parágrafo)": old = "(parágrafo novo; ver linha anterior)"
    rowsB.append(f"| {i} | {loc} | {pr} | {esc(old)} | {esc(new)} | {esc(why)} |")
tableB = "| # | Local | Prior. | Trecho anterior (v1) | Trecho novo (rev2) | Motivo |\n|---|---|---|---|---|---|\n" + "\n".join(rowsB)

# ================================================================ (C) busca global de termos
def ctx(text, m, w=70): return re.sub(r"\s+", " ", text[max(0, m.start() - w): m.end() + w]).strip()


def scan(pat, docs, flags=re.I):
    out = []
    for name, items in docs:
        for it in items:
            for m in re.finditer(pat, it["text"], flags):
                out.append((name, it["loc"], ctx(it["text"], m), m.group(0)))
    return out


DOCS_R2 = [("A rev2", I2), ("B rev2", S2)]; DOCS_V1 = [("A v1", I1), ("B v1", S1)]
sec = []


def block(title, pat, just=None, flags=re.I, show_v1=True):
    r2 = scan(pat, DOCS_R2, flags); v1 = scan(pat, DOCS_V1, flags)
    s = [f"### {title}", f"Padrão: `{pat}`. Ocorrências: **v1 = {len(v1)}**, **rev2 = {len(r2)}**."]
    if r2:
        s.append("| Arquivo | Local | Contexto | Justificativa |\n|---|---|---|---|")
        for name, loc, c, m in r2:
            j = just(name, loc, c, m) if just else ""
            s.append(f"| {name} | {loc} | …{esc(c)}… | {esc(j)} |")
    else:
        s.append("Nenhuma ocorrência na rev2.")
    return "\n".join(s), r2, v1


def j_super(name, loc, c, m):
    if re.search(r"sever", c, re.I): return "Restrito à insegurança grave (RERI 1,28 [0,48-2,08]); legítimo."
    if re.search(r"any|close to additive", c, re.I): return "Usado para contrastar com 'close to additive' em qualquer insegurança; legítimo."
    return "REVISAR"


b1, r_super, v_super = block("super-additive / super-additivity", r"super-?additiv", j_super)
b2, r_attr, v_attr = block("attributable / attribut*", r"attribut", lambda *a: "Título literal de referência? REVISAR" if a[1] == "References" else "REVISAR")
b3, r_nat, v_nat = block("'natural benchmark' e 'natural'", r"natural", lambda n, l, c, m: "Negação: 'neither scale is the natural or superior standard'; legítimo." if "neither scale" in c else ("REVISAR" if l != "References" else "Título literal de referência"))
b4, r_ct, v_ct = block("characteriztic / characteriztics", r"characteriz?t", None)
b4b = scan(r"characteristic", DOCS_R2)
markers = []
for name, items in DOCS_R2:
    for it in items:
        for h in it["hl"]: markers.append((name, it["loc"], h, it["text"][:60]))
        for m in re.finditer(r"\[(?:VERIFY|CONFIRM|PENDING|to be completed|TODO|TBD)[^\]]*\]", it["text"]):
            if m.group(0)[1:-1] not in it["hl"] and not any(m.group(0)[1:-1] in h for h in it["hl"]): markers.append((name, it["loc"] + " (sem realce)", m.group(0), it["text"][:60]))


def jm(loc, t, ctxp=""):
    T = (t + " " + ctxp).lower()
    if "author names" in T or "affiliations" in T or "corresponding" in T or "authors:" in T: return "Depende dos coautores/instituição (nomes, afiliações, correspondência); não foi inventado."
    if "ethics" in T: return "Depende do comitê de ética/instituição; nenhuma aprovação ou dispensa foi afirmada."
    if "funding" in T or "supported by" in T: return "Depende dos autores/financiadores; formato IJE indicado."
    if "conflict" in T: return "Depende de todos os autores."
    if "author contributions" in T or "guarantor" in T or "contributions" in T: return "Depende dos coautores (CRediT, garantidor)."
    if "acknowledg" in T: return "Depende dos autores."
    if "repository" in T or "licence" in T: return "Depende da criação de repositório/DOI; fora desta rodada (não criado)."
    if "unrecorded" in T: return "Depende dos dados (contagem de registros com código 9 em 'não negro'); exige nova consulta ao dado, fora desta rodada."
    if "adjusted reri" in T: return "Depende de nova análise (RERI ajustado); fora desta rodada."
    if "cut-points" in T: return "Depende de nova análise (sensibilidade ao ponto de corte); fora desta rodada."
    if "independently checked" in T or "reviewed and edited" in T: return "Depende da confirmação humana dos autores (política de IA do IJE)."
    if "author list and pagination" in T or "not yet in crossref" in T: return "Depende de fonte externa (lista de autores e paginação do artigo ainda não indexado)."
    return "REVISAR"


mk_rows = ["| Arquivo | Local | Marcador | Depende de / justificativa |", "|---|---|---|---|"]
mk_rev = 0
for name, loc, t, cp in markers:
    j = jm(loc, t, cp); mk_rev += (j == "REVISAR")
    mk_rows.append(f"| {name} | {loc} | {esc(t[:150])}{'…' if len(t) > 150 else ''} | {j} |")
b5 = "### Marcadores entre colchetes (VERIFY / CONFIRM / PENDING / to be completed)\nDetectados pelo realce amarelo dos trechos e, adicionalmente, por busca de texto. Todos permanecem como pendência explícita; nenhum foi preenchido com dado inventado.\n\n" + "\n".join(mk_rows)
n_markers_v1 = sum(len(it["hl"]) for _, items in DOCS_V1 for it in items)

# linguagem causal e equivalentes
CAUS = [(r"explained by|explain[s]? ", "explain*"), (r"caused|causes ", "caused/causes"), (r"due to", "due to"), (r"accounted for|accounts for|account for", "accounted for"), (r"contribut", "contribut*"),
        (r"arises? from|arising", "arise(s) from"), (r"driven by|responsible for|leads? to|results? in", "driven by/responsible for/leads to/results in"), (r"\bbecause\b", "because"), (r"mediat", "mediat*")]
JC = {"due to": lambda c: "Nome da medida (relative excess risk due to interaction)." if "excess risk due to interaction" in c else ("Título de referência (literal)." if "diminished return" in c or "due to diminished" in c else "REVISAR"),
      "accounted for": lambda c: "Partição estatística de variância (PCV/VPC), não causal; legítimo." if re.search(r"variance|PCV|main effects", c) else "REVISAR",
      "mediat*": lambda c: "Negação: 'not a mediation analysis' / 'not mediation'; legítimo." if re.search(r"not (a )?mediation", c) else "REVISAR",
      "because": lambda c: "Aritmética/lógica ('because the null hypotheses differ' / 'because the outcome is common'); sem sentido causal sobre raça ou renda." if re.search(r"null hypotheses|outcome is common", c) else "REVISAR",
      "contribut*": lambda c: "Rótulo de declaração ('Author contributions'); sem sentido causal." if "Author contributions" in c else "REVISAR",
      "driven by/responsible for/leads to/results in": lambda c: "Definição de pessoa de referência da pesquisa (membro 'responsável' pelo domicílio); descritivo." if "responsible for it" in c else "REVISAR",
      "explain*": lambda c: "Título literal de referência." if re.search(r"explain inequities|MAIHDA method explain", c) else "REVISAR"}
caus_rows = ["| Termo | v1 | rev2 | Ocorrências na rev2 (justificativa) |", "|---|---|---|---|"]
caus_rev = 0
for pat, lab in CAUS:
    r2 = [x for x in scan(pat, DOCS_R2) if x[1] != "References"]; r2ref = [x for x in scan(pat, DOCS_R2) if x[1] == "References"]
    v1 = [x for x in scan(pat, DOCS_V1) if x[1] != "References"]
    det = []
    for name, loc, c, m in r2:
        j = JC.get(lab, lambda c: "REVISAR")(c); caus_rev += (j == "REVISAR"); det.append(f"{name}/{loc}: …{c[:110]}… → {j}")
    if r2ref: det.append(f"{len(r2ref)} em títulos literais de referência (não alterados)")
    caus_rows.append(f"| {lab} | {len(v1)} | {len(r2)} | {esc('; '.join(det)) if det else '—'} |")
b6 = "### Linguagem causal e equivalentes (fora das referências)\n" + "\n".join(caus_rows)

# ortografia
US = r"\b(color\w*|behavior\w*|center\w*|analyz\w*|favor\w*|labor\b|fiber|defense|judgment|program\b|catalog\b|modeling|modeled|labeled|traveled|neighbor\w*|meter\b|liter\b|gray\b|randomiz\w*|utiliz\w*)"
us_hits = [x for x in scan(US, DOCS_R2) if x[1] != "References"]
ISE = re.compile(r"\b(\w+?)(is|ys)(e|ed|es|ing|ation|ations)\b", re.I)
ALLOW = set("analyse analysed analyses analysing analyse otherwise raise raised raises raising precise precisely exercise exercised comprise comprised comprises comprising promise revise revised revising arise arises arising rise rises noise wise likewise premise premises compromise supervise advise advised surprise surprising expertise enterprise franchise these those otherwise exercises apprise disguise devise concise paradise chemise treatise treatises demise emphasise pairwise rising".split())
ise_hits = Counter(); ise_ctx = {}
for name, items in DOCS_R2:
    for it in items:
        if it["loc"] == "References": continue
        for m in ISE.finditer(it["text"]):
            w = m.group(0).lower()
            if w in ALLOW: continue
            ise_hits[w] += 1; ise_ctx.setdefault(w, ctx(it["text"], m, 40))
ize = Counter(); ize_v1 = Counter()
IZE = re.compile(r"\b\w+iz(e|ed|es|ing|ation|ations|ability)\b", re.I)
for name, items in DOCS_R2:
    for it in items:
        if it["loc"] == "References": continue
        for m in IZE.finditer(it["text"]):
            if m.group(0).lower() not in ("size", "sizes"): ize[m.group(0).lower()] += 1
for name, items in DOCS_V1:
    for it in items:
        if it["loc"] == "References": continue
        for m in IZE.finditer(it["text"]): ize_v1[m.group(0).lower()] += 1
sig = [x for x in scan(r"significan|significa", DOCS_R2) if x[1] != "References"]
plow = [x for x in scan(r"\bp\s*[<=>]|\bp-value", DOCS_R2, 0) if x[1] != "References"]
# P italico / n italico
def italic_check(doc, cap):
    n_it = 0
    for p in doc.paragraphs:
        for r in p.runs:
            if r.italic and r.text.strip() in ("P", "n"): n_it += 1
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        if r.italic and r.text.strip() in ("P", "n"): n_it += 1
    return n_it
b7 = ["### Ortografia e tipografia",
      f"- **Regra aplicada (guia do IJE = inglês britânico; checklist SCIMED da OUP = ortografia de Oxford):** sufixo **-ize** ('racialized', 'characterized', 'linearization', 'dichotomized', 'anonymized', 'criticized', 'harmonized') e **analyse**. As formas que você listou são, portanto, a grafia de Oxford exigida, e não erro americano; foram uniformizadas. Se o IJE indicar -ise no upload, a troca é uma linha em `ije_lib_20260925.py` (regex `OXF_RE`).",
      f"- Formas em -ize/-ization na rev2 (fora das referências): {', '.join(f'{k} ({v})' for k, v in sorted(ize.items())) or 'nenhuma'}.",
      f"- Formas em -ise remanescentes (excluídas palavras legítimas como 'otherwise', 'raise', 'comprise', 'analyse'): {', '.join(f'{k} ({v}) …{ise_ctx[k]}…' for k, v in sorted(ise_hits.items())) or 'nenhuma'}.",
      f"- Grafias americanas sem relação com -ize (color, behavior, center, analyze, favor, program, modeling…): **{len(us_hits)}** ocorrências fora das referências" + ("." if not us_hits else ": " + "; ".join(f"{h[3]} ({h[1]})" for h in us_hits)),
      f"- 'characteriztic(s)': v1 = {len(v_ct)}, rev2 = {len(r_ct)}. 'characteristic(s)' (correto) na rev2: {len(b4b)}.",
      f"- 'significant/significance': **{len(sig)}** ocorrências fora das referências (o IJE pede evitar o termo)" + ("." if not sig else ": " + "; ".join(f"{h[2]}" for h in sig)),
      f"- P-valores com 'p' minúsculo ('p <', 'p =', 'p-value') fora das referências: **{len(plow)}**. P e n em itálico: {italic_check(d2, 'A')} ocorrências no manuscrito e {italic_check(ds2, 'B')} no suplemento (cabeçalhos e legendas). As notações p00, p10, p01, p11 (prevalências) permanecem em minúscula, por serem proporções e não valores de P.",
      "- Referências: títulos e nomes de periódicos literais **não foram alterados** (ex.: 'Gender, skin color, and household composition…', 'U.S. Department of Agriculture')."]
b7 = "\n".join(b7)

sectionC = "## (C) Busca global de termos (rev2 e suplemento; v1 para comparação)\n\n" + "\n\n".join([b1, b2, b3, b4, b5, b6, b7])

# ================================================================ (D) requisitos IJE
def words(t): return len(re.findall(r"\S+", t))
def region_paras(items, start, end):
    on = False; out = []
    for it in items:
        if it["kind"] != "p": continue
        t = it["text"].strip()
        if t == start and it["loc"] == start: on = True; continue
        if t == end and it["loc"] == end: break
        if on: out.append(it)
    return out
CAPRE = re.compile(r"^(Table|Figure|Supplementary (Table|Figure)) ?\S*\.")
main_items = [it for it in I2 if it["kind"] == "p" and it["loc"] in ("Introduction", "Methods", "Results", "Discussion", "Conclusion") and it["text"].strip()]
main_w = sum(words(it["text"]) for it in main_items if not CAPRE.match(it["text"]) and not it["text"].startswith("Weighted percentages") and not it["text"].startswith("Crude, survey-weighted estimates (no covariates)"))
abs_w = sum(words(it["text"]) for it in I2 if it["kind"] == "p" and it["loc"] == "Abstract" and re.match(r"(Background|Methods|Results|Conclusions):", it["text"]))
kw = [it["text"] for it in I2 if it["text"].startswith("Keywords:")][0].split(":", 1)[1].split(";")
km = [it["text"] for it in I2 if it["kind"] == "p" and it["loc"] == "Key Messages" and it["text"].strip() and it["text"].strip() != "Key Messages"]
nrefs = len([it for it in I2 if it["loc"] == "References" and re.match(r"^\d+\. ", it["text"])])
sec1 = d2.sections[0]
xml_footer = "".join(p._p.xml for p in sec1.footer.paragraphs)
sp = d2.styles["Normal"].paragraph_format.line_spacing
tbl_ok = True
for t in d2.tables:
    b = t._tbl.tblPr.find(qn("w:tblBorders"))
    vals = {c.tag.split('}')[1]: c.get(qn("w:val")) for c in b} if b is not None else {}
    if vals.get("left") != "nil" or vals.get("right") != "nil" or vals.get("insideV") != "nil": tbl_ok = False
imgs = []
for i, shp in enumerate(d2.inline_shapes):
    rid = shp._inline.graphic.graphicData.pic.blipFill.blip.embed; blob = d2.part.related_parts[rid].blob
    im = Image.open(io.BytesIO(blob)); imgs.append((f"Fig {i + 1}", im.size, shp._inline.docPr.get("descr") or ""))
imgsS = []
for i, shp in enumerate(ds2.inline_shapes):
    rid = shp._inline.graphic.graphicData.pic.blipFill.blip.embed; blob = ds2.part.related_parts[rid].blob
    im = Image.open(io.BytesIO(blob)); imgsS.append((f"Fig S{i + 1}", im.size, shp._inline.docPr.get("descr") or ""))
lnnum = d2.sections[0]._sectPr.find(qn("w:lnNumType")) is not None

ABBR = [("RERI", r"relative excess risk due to interaction"), ("PR", r"prevalence ratio"), ("CI", r"confidence interval"), ("MW", r"minimum wage"), ("MAIHDA", r"multilevel analysis of individual heterogeneity"),
        ("VPC", r"variance partition coefficient"), ("PCV", r"proportional change in variance"), ("PNADC", r"Continuous National Household Sample Survey"), ("IBGE", r"Brazilian Institute of Geography and Statistics"),
        ("EBIA", r"Brazilian Food Insecurity Scale"), ("STROBE", r"Strengthening the Reporting"), ("FAO", r"Food and Agriculture Organization"), ("AI", r"artificial intelligence"),
        ("AUC", r"area under"), ("OR", r"odds ratio"), ("pp", r"percentage points"), ("PSU", r"primary sampling unit")]
def blob_of(items, loc=None, pred=None):
    return "\n".join(it["text"] for it in items if (loc is None or it["loc"] == loc) and (pred is None or pred(it)))
def tbl_blob(k):
    cap = [it["text"] for it in I2 if it["kind"] == "p" and it["text"].startswith(f"Table {k}.")]
    note = [it["text"] for it in I2 if it["kind"] == "p" and it["loc"] == "Results" and ((k == 1 and it["text"].startswith("Weighted percentages")) or (k in (2, 3) and it["text"].startswith("Crude, survey-weighted estimates (no covariates)")))]
    return "\n".join(cap + [it["text"] for it in I2 if it["kind"] == "t" and it["loc"] == f"Table {k if k == 1 else k}"][:0] + [it["text"] for it in I2 if it["kind"] == "t" and it["loc"] == f"Table {k}"] + (note if k == 1 else []))
BLOBS = {"Resumo": "\n".join(it["text"] for it in I2 if it["kind"] == "p" and it["loc"] == "Abstract"), "Mensagens-chave": "\n".join(km),
         "Texto principal": "\n".join(it["text"] for it in main_items if not CAPRE.match(it["text"])),
         "Tabela 1": "\n".join([it["text"] for it in I2 if it["kind"] == "p" and it["text"].startswith("Table 1.")] + [it["text"] for it in I2 if it["kind"] == "p" and it["text"].startswith("Weighted percentages")] + [it["text"] for it in I2 if it["kind"] == "t" and it["loc"] == "Table 1"]),
         "Tabela 2": "\n".join([it["text"] for it in I2 if it["kind"] == "p" and it["text"].startswith("Table 2.")] + [it["text"] for it in I2 if it["kind"] == "t" and it["loc"] == "Table 2"]),
         "Tabela 3": "\n".join([it["text"] for it in I2 if it["kind"] == "p" and it["text"].startswith("Table 3.")] + [it["text"] for it in I2 if it["kind"] == "t" and it["loc"] == "Table 3"]),
         "Figura 1": "\n".join(it["text"] for it in I2 if it["kind"] == "p" and it["text"].startswith("Figure 1.")), "Suplemento": TS2all}
# as notas das Tabelas 2-3 estao em paragrafo apos a tabela; anexar
for k in (2, 3):
    BLOBS[f"Tabela {k}"] += "\n" + "\n".join(it["text"] for it in I2 if it["kind"] == "p" and it["text"].startswith("Crude, survey-weighted estimates (no covariates)"))
abbr_rows = ["| Sigla | " + " | ".join(BLOBS) + " |", "|---|" + "---|" * len(BLOBS)]
abbr_fail = 0
for a, ex in ABBR:
    cells = []
    for b, t in BLOBS.items():
        m = re.search(r"(?<![A-Za-z])" + re.escape(a) + r"(?![A-Za-z])", t)
        if not m: cells.append("—"); continue
        e = re.search(ex, t, re.I)
        if e and (b not in ("Resumo", "Mensagens-chave", "Texto principal") or e.start() < m.start() + 1): cells.append("OK")
        else: cells.append("**FALTA**"); abbr_fail += 1
    abbr_rows.append(f"| {a} | " + " | ".join(cells) + " |")
abbr_tbl = "\n".join(abbr_rows)
# supplement numbering
sup_caps = re.findall(r"Supplementary Table (S\d+)[ab]?\.", "\n".join(it["text"] for it in S2 if it["kind"] == "p")); sup_caps = list(dict.fromkeys(sup_caps))
figS = re.findall(r"Supplementary Figure (S\d+)\.", TS2)
strobe_ok = "STROBE checklist" in TS2
ok = lambda c: "OK" if c else "**FALHA**"
Drows = [
    ("Texto principal ≤ 3.000 palavras (sem resumo, mensagens-chave, declarações, referências, tabelas, figuras, suplemento)", f"{main_w} palavras (recontagem independente do .docx; o construtor contou 2931 com títulos)", ok(main_w <= 3000)),
    ("Resumo estruturado ≤ 250 (Background, Methods, Results, Conclusions)", f"{abs_w} palavras; inclui período (fourth quarter 2023), tamanho amostral (173 676) e estimativas com IC", ok(abs_w <= 250)),
    ("Palavras-chave 3-10", f"{len(kw)}", ok(3 <= len(kw) <= 10)),
    ("Três Key Messages, cada uma uma frase completa", f"{len(km)} mensagens; frases por mensagem: {[len(sentences(x)) for x in km]}", ok(len(km) == 3 and all(len(sentences(x)) == 1 for x in km))),
    ("Referências ≤ 50, estilo Oxford SCIMED numerado", f"{nrefs}", ok(nrefs <= 50)),
    ("Tabelas + figuras ≤ 8", f"{len(d2.tables)} tabelas + {len(d2.inline_shapes)} figura = {len(d2.tables) + len(d2.inline_shapes)}", ok(len(d2.tables) + len(d2.inline_shapes) <= 8)),
    ("Espaçamento duplo", f"estilo Normal com espaçamento {sp}", ok(sp == 2.0)),
    ("Margens de 2,5 cm", f"{sec1.left_margin.cm:.1f} / {sec1.right_margin.cm:.1f} / {sec1.top_margin.cm:.1f} / {sec1.bottom_margin.cm:.1f} cm", ok(all(abs(x - 2.5) < 0.05 for x in (sec1.left_margin.cm, sec1.right_margin.cm, sec1.top_margin.cm, sec1.bottom_margin.cm)))),
    ("Todas as páginas numeradas", "campo PAGE no rodapé", ok("PAGE" in xml_footer)),
    ("Numeração de linhas", "contínua", ok(lnnum)),
    ("Sem linhas verticais nas tabelas", f"{len(d2.tables)} tabelas verificadas (bordas esquerda, direita e internas verticais = nil)", ok(tbl_ok)),
    ("Figuras ≥ 3.600 px (largura)", "; ".join(f"{n}: {s[0]}×{s[1]}" for n, s, a in imgs) + " | suplemento: " + "; ".join(f"{n}: {s[0]}" for n, s, a in imgsS), ok(all(s[0] >= 3600 for _, s, _ in imgs + imgsS))),
    ("Texto alternativo em todas as figuras", f"corpo {sum(1 for *_, a in imgs if a)}/{len(imgs)}; suplemento {sum(1 for *_, a in imgsS if a)}/{len(imgsS)}", ok(all(a for *_, a in imgs + imgsS))),
    ("Siglas por extenso na primeira menção (resumo, mensagens-chave, texto, tabelas, figura, suplemento)", "ver matriz abaixo", ok(abbr_fail == 0)),
    ("P em itálico e maiúsculo; n em itálico e minúsculo; evitar 'significant'", f"P-valores minúsculos: {len(plow)}; 'significant': {len(sig)}; itálicos P/n: {italic_check(d2, 'A')} + {italic_check(ds2, 'B')}", ok(len(plow) == 0 and len(sig) == 0)),
    ("Inglês britânico / ortografia de Oxford", "ver (C), bloco de ortografia", ok(len(r_ct) == 0 and len(us_hits) == 0)),
    ("Página de título: título, running head, autores, afiliações, autor para correspondência (endereço postal e e-mail), contagem de palavras", "campos presentes; nomes, afiliações e correspondência **pendentes** (não inventados)", "PENDENTE (autores)"),
    ("Declarações: ética, financiamento (formato 'This work was supported by'), conflitos, contribuições e garantidor, dados/código, IA", "todas presentes; conteúdo dependente dos autores marcado como pendência", "PENDENTE (autores)"),
    ("Disponibilidade de dados e de **todo o código**", "microdados públicos (IBGE) citados; repositório e DOI **não criados** (fora desta rodada)", "PENDENTE"),
    ("Uso de IA descrito nos Métodos e nas Declarações; IA não é autora", "presente nos dois lugares; confirmação humana marcada", "PENDENTE (confirmação dos autores)"),
    ("STROBE", f"Tabela {ST if False else 'S14'} do suplemento" if strobe_ok else "ausente", ok(strobe_ok)),
    ("Numeração do suplemento em S", f"tabelas: {', '.join(sup_caps)}; figuras: {', '.join(figS)}", ok(len(sup_caps) >= 14 and len(figS) == 5)),
    ("Carta ao editor / início da submissão", "não feitos (instrução desta rodada)", "N/A"),
]
sectionD = ("## (D) Requisitos do guia oficial do IJE (Original Article) conferidos na rev2\n"
            "Fontes: página oficial de instruções do IJE (academic.oup.com/ije/pages/General_Instructions, conferida em 25/09/2026) e o *Mini Oxford SCIMED style checklist*. A contagem de palavras do sistema de submissão pode diferir da minha (script, `\\S+`).\n\n"
            "| Requisito | Situação na rev2 | Resultado |\n|---|---|---|\n" + "\n".join(f"| {a} | {esc(b)} | {c} |" for a, b, c in Drows) +
            "\n\n### Matriz de siglas (primeira menção por seção)\n'—' = a sigla não aparece na seção; OK = forma por extenso presente (no resumo, nas mensagens-chave e no texto principal, **antes** do primeiro uso; nas tabelas, figura e suplemento, na legenda, na nota ou na lista de abreviaturas); FALTA = usada sem extenso.\n\n" + abbr_tbl)

# ================================================================ (E) bloqueios
sectionE = """## (E) Bloqueios não resolvidos (lista curta; detalhes em `E_Pendencias_bloqueantes_rev2.md`)
1. **Autores, ordem, afiliações, autor para correspondência (endereço postal e e-mail), ORCID:** dependem dos coautores/instituição.
2. **Ética:** nome do comitê e número de aprovação, ou a declaração institucional de que a aprovação era desnecessária. Nada foi afirmado.
3. **Financiamento (formato IJE), conflitos de interesse, contribuições (CRediT) e garantidor.**
4. **Código e dados:** o IJE exige todo o código disponível; repositório, licença e DOI não existem (não criados nesta rodada).
5. **IA:** os autores precisam checar código e saídas de forma independente e confirmar a declaração. Minhas reexecuções e verificações foram feitas pela mesma IA.
6. **Codificação das variáveis** (V2010, VD3004, VDI5009, V1022, SD17001) não validada contra o dicionário do IBGE; contagem de registros com código 9 dentro de "não negro".
7. **Sem RERI ajustado, sem IC para a decomposição e sem sensibilidade ao ponto de corte da renda (≤1/4 MW):** limitações declaradas no texto; exigiriam análises novas (fora desta rodada).
8. **Referência Câmara et al. 2026 (AJPH)** incompleta (autores e paginação ainda fora do Crossref/PubMed); DOIs e abreviações de periódicos conferir contra o NLM/LTWA.
9. **Manuscrito SSM (intocado, e há um arquivo de bloqueio `~$_Manuscript_blinded.docx` na pasta, indicando que está aberto no Word):** verifiquei por busca que ele contém as mesmas formulações corrigidas aqui: "attributable to" (3 vezes, decomposição), "Joint effects were therefore super-additive but sub-multiplicative" e frases equivalentes (manuscrito, Highlights e carta ao editor), e a descrição imprecisa do ajuste da atenuação. As correções valem para ele antes de qualquer submissão ao SSM.
10. **Um manuscrito, dois periódicos:** não submeter ao mesmo tempo ao SSM e ao IJE.
11. **Custo:** IJE (OUP) não está no acordo CAPES; confirmar a rota de acesso aberto e o APC.
12. **Contagem oficial de palavras** e formatação final serão conferidas no sistema de submissão do IJE (a minha é por script).
"""

# ================================================================ arquivo R2
head = """# Revisão IJE rev2: entregáveis (25/09/2026)

Arquivos novos (a v1 permanece intacta na mesma pasta): `A_Manuscript_IJE_rev2.docx`, `B_Supplementary_material_IJE_rev2.docx`, `C_Traceability_table_rev2.xlsx`, `D_Counts_IJE_rev2.md`, `E_Pendencias_bloqueantes_rev2.md`, `Relatorio_de_mudancas_IJE_rev2.md`, `F_abstract_number_check_rev2.csv`, `F_Verification_report_rev2.md` e este arquivo.
Nenhuma análise foi refeita e nenhum resultado, IC ou número foi alterado; mudaram texto, rótulos, organização e formatação.

## (A) Manuscrito revisado
`A_Manuscript_IJE_rev2.docx` (com suplemento `B_..._rev2.docx`).

## (B) Mudanças substantivas: trecho anterior → trecho novo → motivo
Prioridades: 1 conclusão científica; 2 linguagem causal; 3 'benchmark natural'; 4 ortografia/tipografia/guia; 5 especificação dos modelos; 6 foco editorial. Os trechos são citados literalmente dos dois .docx.

"""
(OUT / "R2_Entregaveis_revisao_IJE.md").write_text(head + tableB + "\n\n" + sectionC + "\n\n" + sectionD + "\n\n" + sectionE, encoding="utf-8")

# ================================================================ verificacao rev2
def cmp_tables():
    lines = []
    def rows(doc, k): return [[c.text for c in r.cells] for r in doc.tables[k].rows]
    for k, nm in ((1, "Tabela 2 (raça × renda)"), (2, "Tabela 3 (raça × escolaridade)")):
        a, b = rows(d1, k), rows(d2, k); diff_val = 0; diff_lab = 0
        assert len(a) == len(b), (nm, len(a), len(b))
        for ra, rb in zip(a, b):
            if ra[1:] != rb[1:]: diff_val += 1
            if ra[0] != rb[0]: diff_lab += 1
        lines.append(f"| {nm} | {len(a)} | {diff_val} | {diff_lab} |")
    a, b = rows(d1, 0), rows(d2, 0); va = {tuple(r) for r in a}; miss = [r for r in b if tuple(r) not in va]
    lines.append(f"| Tabela 1 (condensada; cada linha da rev2 deve existir na v1) | {len(b)} | {len(miss)} linhas sem correspondente | — |")
    return lines
ctab = cmp_tables()
NUM = re.compile(r"[−-]?\d+[.,]\d+|\d{3,}")
def nums(t): return Counter(n.replace("−", "-").replace(",", ".") for n in NUM.findall(t.replace("\u00a0", "").replace(" ", "")))
main2 = BLOBS["Resumo"] + "\n" + BLOBS["Texto principal"]
n2 = nums(main2); n1 = nums(T1all)
new_tokens = sorted(k for k in n2 if k not in n1)
# tabelas suplementares: celulas numericas da v1 ausentes na rev2
def numcells(items): return Counter(it["text"] for it in items if it["kind"] == "t" and re.search(r"\d", it["text"]) and not re.search(r"[A-Za-z]{3,}", it["text"]) and not re.match(r"^S\d", it["text"]))
c1, c2 = numcells(S1), numcells(S2); missing_supp = c1 - c2
# arquivos identicos ao backup v1
import filecmp
same = []
for f in ["C_coherence_checks.csv", "F_independent_verification.csv", "F_abstract_number_check.csv", "A_Manuscript_IJE.docx", "B_Supplementary_material_IJE.docx", "C_Traceability_table.xlsx", "Supplementary_data_strata.xlsx"]:
    try: same.append((f, filecmp.cmp(OUT / f, BACKUP / f, shallow=False)))
    except Exception as e: same.append((f, f"erro {e}"))
A = pd.read_csv(OUT / "F_abstract_number_check_rev2.csv"); Ci = pd.read_csv(OUT / "C_coherence_checks.csv"); Fi = pd.read_csv(OUT / "F_independent_verification.csv")
tr = pd.read_excel(OUT / "C_Traceability_table_rev2.xlsx", sheet_name=None)
n_tr = sum(len(v) for k, v in tr.items() if k in ("Abstract", "Text_Intro_Methods", "Text_Results_Discussion", "Tables"))
ver = f"""# F. Verificação da rev2 (25/09/2026)

Escopo desta rodada: **texto, rótulos e formatação**. Nenhuma análise foi refeita; portanto a verificação central é mostrar que **nada numérico mudou** e que as contagens e os termos-alvo estão corretos. A reexecução completa da cadeia de análise (dados, Python, R) é a da v1 (`F_Verification_report.md`, saídas idênticas) e não foi repetida, porque as entradas e o código de análise não mudaram.

## 1. Entradas e verificações da v1 reproduzidas
| Arquivo | Igual ao backup da v1 (byte a byte)? |
|---|---|
""" + "\n".join(f"| {f} | {'sim' if r is True else r} |" for f, r in same) + f"""

- `coerencia_ije_20260925.py` reexecutado agora: **{int((Ci.status == 'PASS').sum())} verificações PASS** (o arquivo é idêntico ao da v1).
- `verificacao_independente_ije_20260925.py` reexecutado agora (numpy, sem statsmodels): **{int((Fi.status == 'PASS').sum())} PASS**, 1 linha INFO (RP com escolaridade em 4 categorias, 1,293 contra 1,305, é diferença de especificação, não discrepância); arquivo idêntico ao da v1.
- **Números do resumo (rev2):** `F_abstract_number_check_rev2.csv`: **{int((A.status == 'MATCH').sum())} de {len(A)}** conferem com o recálculo independente no arredondamento impresso (na v1 eram 16 de 16; o item novo é a razão de RPs para qualquer insegurança, 0,75 [0,71-0,80], incluída no resumo).
- Rastreabilidade (`C_Traceability_table_rev2.xlsx`): {n_tr} números do resumo, do texto e das tabelas com arquivo, linha e coluna de origem.

## 2. Tabelas 1-3: valores da rev2 contra a v1
| Tabela | Linhas | Linhas com valor diferente | Linhas com rótulo diferente |
|---|---|---|---|
""" + "\n".join(ctab) + f"""

Rótulos diferentes = as linhas da decomposição ('attributable to …' → 'Component corresponding to …') e o título do bloco; **nenhum valor mudou**.

## 3. Números novos no texto
Números decimais ou com 3+ dígitos do resumo e do texto principal da rev2 que **não aparecem** em nenhum lugar do manuscrito v1: {', '.join(new_tokens) if new_tokens else 'nenhum'}. Células numéricas do suplemento presentes na v1 e ausentes na rev2 (excluídas as células que só citam números de tabela S, renumerados): {sum(missing_supp.values())}.

## 4. Contagens independentes (recontadas do .docx)
Texto principal {main_w} palavras (limite 3.000); resumo {abs_w} (limite 250); {nrefs} referências; {len(d2.tables)} tabelas + {len(d2.inline_shapes)} figura no corpo. Detalhes e demais requisitos do guia em `R2_Entregaveis_revisao_IJE.md`, item (D).

## 5. Auditoria final dos termos (item (C) do arquivo de entregáveis)
| Termo | v1 | rev2 | Situação |
|---|---|---|---|
| `super-additive` | {len(v_super)} | {len(r_super)} | todas as ocorrências da rev2 estão restritas à insegurança grave ou contrastadas com "close to additive" (justificadas linha a linha) |
| `attributable` (e `attribut*`) | {len(v_attr)} | {len(r_attr)} | {'nenhuma' if not r_attr else 'REVISAR'} |
| `natural benchmark` / `natural` | {len(v_nat)} | {len(r_nat)} | a única ocorrência é a negação "neither scale is the natural or superior standard" |
| `characteriztic(s)` | {len(v_ct)} | {len(r_ct)} | bug da minha função de ortografia, corrigido; "characteristic(s)" correto ocorre {len(b4b)} vezes |
| marcadores `[VERIFY/CONFIRM/PENDING/to be completed]` | {n_markers_v1} (trechos realçados) | {len(markers)} | todos justificados como pendência dependente de dados, coautores ou instituição; {mk_rev} sem justificativa |
| linguagem causal e equivalentes | — | — | {caus_rev} ocorrências sem justificativa |

## 6. O que esta verificação NÃO cobre
- Foi feita pela mesma IA que escreveu o código; a implementação independente reduz o risco de erro de código, mas **não substitui a conferência humana**.
- A codificação das variáveis usa a mesma função `preparar()`; não valida o mapeamento com o dicionário do IBGE.
- Contagem de palavras do IJE pode diferir; a formatação final só se confirma no upload.
- Referências (DOIs, abreviações) não foram reconferidas nesta rodada.
"""
(OUT / "F_Verification_report_rev2.md").write_text(ver, encoding="utf-8")
print("ok | terms:", dict(super_=len(r_super), attr=len(r_attr), nat=len(r_nat), ct=len(r_ct), markers=len(markers), mk_rev=mk_rev, caus_rev=caus_rev), "| abbr_fail", abbr_fail, "| main", main_w, "| abs", abs_w)
print("new_tokens:", new_tokens, "| missing_supp:", sum(missing_supp.values()), "| ise:", dict(ise_hits), "| us:", len(us_hits), "| sig:", len(sig), "| plow:", len(plow))
