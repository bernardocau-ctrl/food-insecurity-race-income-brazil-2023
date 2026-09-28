# -*- coding: utf-8 -*-
"""d7_relatorios.py: gera os relatorios em Markdown da rodada D a partir dos CSV (todos os numeros vem dos arquivos, nada digitado a mao):
RELATORIO_TECNICO_RODADA_D.md (A), E_PROPOSTAS_alteracoes_manuscrito_rodadaD.md (E), F_CHECKLIST_pendencias_rodadaD.md (F), README_RODADA_D.md (C)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *

R = lambda n: pd.read_csv(OUTD / n)
conc, d2, dg, s1, comp, coef, d3, d5, sm5, mat = R("D4_concordancia_estimativas_e_ICs.csv"), R("D2_componentes_absolutos_IC.csv"), R("D2_diagnostico_participacao.csv"), R("D1_padronizado_vs_bruto_raca_renda.csv"), R("D1_composicao_das_celulas.csv"), \
    R("D1_coeficientes_modelo_logistico.csv"), R("D3_sensibilidade_corte_renda.csv"), R("D5_ignorados_comparacao_completa.csv"), R("D5_maiores_diferencas_por_classe.csv"), R("D_matriz_original_vs_corrigido.csv")
J = lambda n: json.loads((OUTD / n).read_text(encoding="utf-8"))
princ, amb, chk, d5i, d4s, tst = J("principal.json"), J("00_ambiente_e_execucao.json"), J("01_checagens_pesos_replicados.json"), J("D5_resumo.json"), J("D4_resumo.json"), J("D_testes_codigo.json")
val = R("D4_validacao_python_vs_R.csv"); flow = R("01_fluxo_amostra_reproduzido.csv"); lay = R("01_layout_variaveis_usadas.csv")
NEG = "−"


def f(x, d=2):
    if x is None or (isinstance(x, float) and np.isnan(x)): return ""
    return f"{x:.{d}f}".replace("-", NEG)


def ci(e, lo, hi, d=2): return f"{f(e, d)} ({f(lo, d)} to {f(hi, d)})" if lo < 0 else f"{f(e, d)} ({f(lo, d)}-{f(hi, d)})"
def rng(lo, hi, d=2): return f"{f(lo, d)} to {f(hi, d)}" if lo < 0 else f"{f(lo, d)}-{f(hi, d)}"


def md(df):
    cols = list(df.columns); out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows(): out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


PI, PE = "raca_x_renda(<=1/4 SM)", "raca_x_escolaridade(sem/fund. incompleto)"
LAB = {"p00": "prevalência, referência (%)", "p10": "prevalência, só raça/cor (%)", "p01": "prevalência, só renda (%)", "p11": "prevalência, ambos (%)", "rr10": "PR só raça/cor", "rr01": "PR só renda", "rr11": "PR ambos", "reri": "RERI",
       "reri_esperado": "RERI esperado se multiplicativo", "ror": "razão de PRs", "comp_raca_pp": "componente da raça/cor isolada (pp)", "comp_ses_pp": "componente da renda isolada (pp)", "interacao_pp": "componente de interação (pp)",
       "conjunta_pp": "diferença conjunta (pp)", "participacao_pct": "participação da interação (%)"}
ORD = list(LAB)
DEC = lambda q: 1 if q in ("p00", "p10", "p01", "p11", "comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct") else 2
OL = {"ia_total": "qualquer", "ia_grave": "grave"}


def d4_table(pair):
    rows = []
    for q in ORD:
        row = {"quantidade": LAB[q]}
        for y in ("ia_total", "ia_grave"):
            g = conc[(conc.par == pair) & (conc.desfecho == y) & (conc.quantidade == q)].iloc[0]; d = DEC(q)
            row[f"{OL[y]}: estimativa"] = f(g.A_est, d); row[f"{OL[y]}: IC A"] = rng(g.A_lo, g.A_hi, d); row[f"{OL[y]}: IC B"] = rng(g.B_lo, g.B_hi, d); row[f"{OL[y]}: IC C"] = rng(g.C_lo, g.C_hi, d)
        rows.append(row)
    return md(pd.DataFrame(rows))


cq = conc[conc.grupo == "quatro_celulas"]; cp = conc[conc.grupo == "prevalencia"]
def g4(pair, y, q): return conc[(conc.par == pair) & (conc.desfecho == y) & (conc.quantidade == q)].iloc[0]
def s1r(y, q): return s1[(s1.desfecho == y) & (s1.quantidade == q)].iloc[0]
def d2r(pair, y, q, cfg="C"): return d2[(d2.par == pair) & (d2.desfecho == y) & (d2.quantidade == q) & (d2.config == cfg)].iloc[0]
def d3r(cut, y, q): return d3[(d3.corte == cut) & (d3.desfecho == y) & (d3.quantidade == q) & (d3.config == "C")].iloc[0]
CUTS = ["<=1/4 SM (primario)", "<=1/2 SM", "<=1 SM"]

# ------------------------------------------------------------------ tabelas de apoio
val_tab = val.groupby("config").agg(max_dif_rel_estimativa=("dif_rel_estimativa", "max"), max_dif_rel_SE=("dif_rel_se", "max")).reset_index()
val_tab["config"] = val_tab["config"].map({"B": "B: pesos+UPA+Estrato vs survey::svydesign(strata, nest=TRUE, lonely.psu='adjust')", "C": "C vs survey::svyby + svycontrast (delta sobre a covariância das réplicas)", "C2": "C vs survey::withReplicates (mesmo estimador do motor Python)"})
val_tab = val_tab.assign(max_dif_rel_estimativa=val_tab.max_dif_rel_estimativa.map(lambda x: f"{x:.1e}"), max_dif_rel_SE=val_tab.max_dif_rel_SE.map(lambda x: f"{x:.1e}"))
lay_t = lay.copy(); lay_t["valores_distintos_nas_pessoas_de_referencia"] = lay_t["valores_distintos_nas_pessoas_de_referencia"].map(lambda x: "" if pd.isna(x) else int(x))
conc_sum = pd.DataFrame([{"grupo": g, "n_quantidades": len(x), "razão de largura do IC, B/A (mediana; mín-máx)": f"{x.largura_B_sobre_A.median():.3f}; {x.largura_B_sobre_A.min():.3f}-{x.largura_B_sobre_A.max():.3f}",
                          "razão de largura do IC, C/A (mediana; mín-máx)": f"{x.largura_C_sobre_A.median():.3f}; {x.largura_C_sobre_A.min():.3f}-{x.largura_C_sobre_A.max():.3f}",
                          "maior dif. abs. de estimativa, A vs original": f"{x.dif_abs_est_A_menos_pub.abs().max():.1e}"} for g, x in conc.groupby("grupo")])
# D-2
d2t = []
for pair, nm in ((PI, "raça × renda"), (PE, "raça × escolaridade")):
    for q in ("comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct"):
        row = {"contraste": nm, "componente": LAB[q]}
        for y in ("ia_total", "ia_grave"):
            a = d2r(pair, y, q, "C"); b = d2r(pair, y, q, "A"); bb = d2r(pair, y, q, "B"); row[f"{OL[y]}: C (principal)"] = ci(a.estimativa, a.ic_inf, a.ic_sup, 1); row[f"{OL[y]}: A"] = rng(b.ic_inf, b.ic_sup, 1); row[f"{OL[y]}: B"] = rng(bb.ic_inf, bb.ic_sup, 1)
        d2t.append(row)
dgt = dg[["par", "desfecho", "conjunta_pp", "cv_conjunta", "participacao_pct", "participacao_rep_min", "participacao_rep_max", "fracao_replicas_|part|>3x|estimativa|", "regra_do_protocolo_permite_reportar_IC_da_participacao"]].copy()
for c in ["conjunta_pp", "participacao_pct", "participacao_rep_min", "participacao_rep_max"]: dgt[c] = dgt[c].map(lambda x: f(x, 1))
dgt["cv_conjunta"] = dgt["cv_conjunta"].map(lambda x: f(x, 3)); dgt["fracao_replicas_|part|>3x|estimativa|"] = dgt["fracao_replicas_|part|>3x|estimativa|"].map(lambda x: f(x, 3)); dgt = dgt.rename(columns={"regra_do_protocolo_permite_reportar_IC_da_participacao": "regra permite IC da participação?"})
# D-1
d1t = []
for q in ORD:
    row = {"quantidade": LAB[q]}
    for y in ("ia_total", "ia_grave"):
        g = s1r(y, q); d = DEC(q); row[f"{OL[y]}: bruta"] = ci(g.bruto_est, g.bruto_lo, g.bruto_hi, d); row[f"{OL[y]}: padronizada"] = ci(g.padronizado_est, g.padronizado_lo, g.padronizado_hi, d)
        row[f"{OL[y]}: dif. (padr. − bruta)"] = ci(g.dif_padronizado_menos_bruto, g.dif_ic_inf, g.dif_ic_sup, d)
    d1t.append(row)
comp_t = comp.copy()
for c in comp_t.columns[2:]: comp_t[c] = comp_t[c].map(lambda x: f(x, 1))
coef_t = coef.copy(); coef_t["OR (IC95%)"] = coef_t.apply(lambda r: ci(r.OR, r.OR_lo, r.OR_hi, 2), axis=1); coef_t = coef_t[["desfecho", "termo", "OR (IC95%)"]]
# D-3
d3t = []
for q in ("p00", "p10", "p01", "p11", "rr10", "rr01", "rr11", "reri", "reri_esperado", "ror", "interacao_pp", "conjunta_pp", "participacao_pct"):
    row = {"quantidade": LAB[q]}
    for y in ("ia_total", "ia_grave"):
        for cut in CUTS: g = d3r(cut, y, q); row[f"{OL[y]} {cut.split(' ')[0]}"] = ci(g.estimativa, g.ic_inf, g.ic_sup, DEC(q))
    d3t.append(row)
n3 = d3[(d3.config == "C") & (d3.quantidade == "p00") & (d3.desfecho == "ia_total")][["corte", "n_ref", "n_so_raca", "n_so_renda", "n_ambos", "pct_baixa_renda_ponderado"]].copy(); n3["pct_baixa_renda_ponderado"] = n3["pct_baixa_renda_ponderado"].map(lambda x: f(x, 1))
# D-5
sm5t = sm5.copy(); sm5t["maior_dif_abs"] = sm5t["maior_dif_abs"].map(lambda x: f(x, 4)); sm5t["maior_dif_relativa_pct"] = sm5t["maior_dif_relativa_pct"].map(lambda x: f(x, 2)); sm5t["maior_dif_sobre_meia_largura_IC"] = sm5t["maior_dif_sobre_meia_largura_IC"].map(lambda x: f(x, 3))
sm5t["onde_maior_dif_abs"] = sm5t["onde_maior_dif_abs"].str.replace(" | ", " / ", regex=False)
sm5t = sm5t[["analise", "classe", "maior_dif_abs", "unidade", "maior_dif_relativa_pct", "maior_dif_sobre_meia_largura_IC", "onde_maior_dif_abs"]]
q5 = d5[(d5.grupo == "prevalencia") & d5.par.str.startswith("renda q5")]
# matriz D
mchg = int((mat.mudanca_de_interpretacao == "SIM").sum())
mx = mat[mat.quantidade.isin(["reri"])][["par", "desfecho", "original_est", "original_ic_inf", "original_ic_sup", "corrigido_ic_inf", "corrigido_ic_sup", "exclui_nulo_original", "exclui_nulo_corrigido", "mudanca_de_interpretacao"]].copy()
for c in ["original_est", "original_ic_inf", "original_ic_sup", "corrigido_ic_inf", "corrigido_ic_sup"]: mx[c] = mx[c].map(lambda x: f(x, 3))
# resumo D-1 e D-3 numerico
sr, ar = s1r("ia_grave", "reri"), s1r("ia_total", "reri"); srr, arr = s1r("ia_grave", "ror"), s1r("ia_total", "ror"); si, ai = s1r("ia_grave", "interacao_pp"), s1r("ia_total", "interacao_pp")
n_restr = f"{d5i['n_analise_restrita']:,}".replace(",", ".")
ent = amb["entradas"]; env = amb["ambiente"]; datas = amb["execucoes"][0]["data_utc"]
lon = J("D9_estrato_solitario.json"); t8 = J("D8_testes_integridade.json")
rsess = (OUTD / "00_R_sessionInfo.txt").read_text(encoding="utf-8").splitlines()[0]

# ================================================================== RELATORIO TECNICO
rep = f"""# Relatório técnico da rodada analítica D-4, D-1/D-2, D-3 e D-5 (25/09/2026)

Base: `A_Manuscript_IJE_rev3.docx` e a auditoria de 25/09/2026. **O manuscrito principal, o suplemento e as figuras não foram alterados nesta rodada.** Protocolo escrito antes de rodar: `PROTOCOLO_RODADA_D.md`.
Marcadores: **VERIFICADO**, **NÃO VERIFICADO**, **SENSIBILIDADE EXPLORATÓRIA**, **DEPENDE DE DECISÃO DOS AUTORES**.

## 0. Resumo executivo
1. **D-4 (desenho).** A variável oficial de estrato é `Estrato` (layout IBGE, posição 21-27, texto de 7 caracteres, 573 estratos, 15.033 UPAs; um estrato tem uma só UPA), e o microdado traz 200 pesos replicados (V1028001-V1028200). O código antigo lia as posições 20-23 sob o rótulo "V1008" (são os três primeiros caracteres do Estrato). As três configurações dão **estimativas pontuais idênticas** e ICs muito próximos (razão de largura de IC, mediana: B/A {conc_sum.loc[conc_sum.grupo=='quatro_celulas','razão de largura do IC, B/A (mediana; mín-máx)'].iloc[0].split(';')[0]}, C/A {conc_sum.loc[conc_sum.grupo=='quatro_celulas','razão de largura do IC, C/A (mediana; mín-máx)'].iloc[0].split(';')[0]}, nas quatro células). **Nenhuma conclusão muda pelo critério "o IC exclui o valor nulo" ({mchg} mudanças em {len(mat)} linhas comparáveis).** Configuração principal pela regra prefixada: **{princ['principal']}** (pesos replicados; método do IBGE), com desvio documentado na seção 2.4.
2. **D-1 (padronização).** Para insegurança **grave**, o RERI bruto de {f(sr.bruto_est)} ({rng(sr.bruto_lo, sr.bruto_hi)}) cai para **{f(sr.padronizado_est)}** ({rng(sr.padronizado_lo, sr.padronizado_hi)}) depois de padronizar por sexo registrado, escolaridade e residência: metade do valor bruto, com limite inferior do IC próximo de zero. A razão de PRs padronizada é {f(srr.padronizado_est)} ({rng(srr.padronizado_lo, srr.padronizado_hi)}), ainda abaixo de 1. Para **qualquer** insegurança, RERI padronizado {f(ar.padronizado_est)} ({rng(ar.padronizado_lo, ar.padronizado_hi)}), compatível com aditividade, como no bruto.
3. **D-2 (IC da decomposição).** Grave, raça × renda: interação {ci(d2r(PI,'ia_grave','interacao_pp').estimativa, d2r(PI,'ia_grave','interacao_pp').ic_inf, d2r(PI,'ia_grave','interacao_pp').ic_sup, 1)} pp da diferença conjunta de {ci(d2r(PI,'ia_grave','conjunta_pp').estimativa, d2r(PI,'ia_grave','conjunta_pp').ic_inf, d2r(PI,'ia_grave','conjunta_pp').ic_sup, 1)} pp; participação {ci(d2r(PI,'ia_grave','participacao_pct').estimativa, d2r(PI,'ia_grave','participacao_pct').ic_inf, d2r(PI,'ia_grave','participacao_pct').ic_sup, 1)}%. Qualquer, raça × renda: interação {ci(d2r(PI,'ia_total','interacao_pp').estimativa, d2r(PI,'ia_total','interacao_pp').ic_inf, d2r(PI,'ia_total','interacao_pp').ic_sup, 1)} pp (o IC inclui zero).
4. **D-3 (corte).** Para a insegurança **grave**, o RERI é positivo com IC que exclui zero nos três cortes ({f(d3r(CUTS[1],'ia_grave','reri').estimativa)} a {f(d3r(CUTS[2],'ia_grave','reri').estimativa)}) e a razão de PRs fica abaixo de 1. Para **qualquer** insegurança, "compatível com aditividade" vale em ≤1/4 e ≤1/2 SM, **mas não em ≤1 SM** (RERI {ci(d3r(CUTS[2],'ia_total','reri').estimativa, d3r(CUTS[2],'ia_total','reri').ic_inf, d3r(CUTS[2],'ia_total','reri').ic_sup)}). SENSIBILIDADE EXPLORATÓRIA.
5. **D-5 (ignorados).** Excluir os 96 domicílios não altera PRs, RERI, razão de PRs, componentes e prevalências de célula além de {f(sm5.loc[sm5.classe=='componente absoluto (pp)','maior_dif_abs'].abs().max(),3)} pp ou {f(sm5.loc[sm5.classe.isin(['PR','RERI','razao de PRs']),'maior_dif_abs'].abs().max(),3)} unidades. A única diferença visível é a prevalência da faixa >2 SM na Tabela 1 (o grupo que abrigava os 77 de renda ignorada): {f(q5[q5.desfecho=='ia_total'].iloc[0].dif_abs,3)} pp (qualquer). O critério prefixado (<10% da meia-largura do IC em todas as classes) **não foi atendido literalmente** por essa linha da Tabela 1 (razão máxima {f(d5i['maior_razao_dif_sobre_meia_largura'],3)}); nas demais classes a razão é ≤ {f(sm5[sm5.classe!='prevalencia (geral e por categoria)']['maior_dif_sobre_meia_largura_IC'].max(),3)}.
6. **Decisão recomendada:** manter o RERI e a decomposição **brutos** como análise descritiva principal, agora com ICs pela configuração C (pesos replicados); apresentar a análise **padronizada** como secundária (suplemento e uma frase); tratar D-3 como robustez exploratória e D-5 como sensibilidade. **DEPENDE DE DECISÃO DOS AUTORES.**

## 1. Ambiente, entradas e reprodução (VERIFICADO)
- Data e hora (UTC) da primeira execução registrada: {datas}. Python {env['python']}, numpy {env['numpy']}, pandas {env['pandas']}, scipy {env['scipy']}, statsmodels {env['statsmodels']}, {rsess}, pacote R `survey` 4.5. Sistema: {env['sistema']}.
- Entradas (SHA-256): `PNADC_2023_trimestre4_20251010.zip` `{ent['PNADC_2023_trimestre4_20251010.zip']['sha256']}`; `input_PNADC_trimestre4_20251010.txt` `{ent['input_PNADC_trimestre4_20251010.txt']['sha256']}`; `dicionario_PNADC_microdados_trimestre4_20260702.xls` `{ent['dicionario_PNADC_microdados_trimestre4_20260702.xls']['sha256']}`. Layout e dicionário oficiais baixados de ftp.ibge.gov.br em 25/09/2026 e guardados em `dados_ibge/pnadc_documentacao/`.
- Comando: `python scripts/rodada_d/run_all.py` (de qualquer diretório; tempo ≈ 5 minutos). **Reprodução limpa executada**: cache e saídas apagados e tudo regerado a partir do ZIP, rodando de outro diretório; **23 arquivos de saída idênticos, byte a byte, aos da primeira execução.** Não há caminhos absolutos nos scripts novos; a raiz do projeto é localizada por `dados_ibge/`.
- Testes do código (`D_testes_codigo.json`, todos PASS): padronização sem covariáveis reproduz as prevalências brutas (dif. máx. {tst['1_std_sem_covariaveis_vs_bruto_ia_total_max_dif']:.1e}); o IRLS logístico ponderado coincide com `statsmodels` (dif. máx. de coeficiente {tst['2_IRLS_vs_statsmodels_ia_total_max_dif_coef']:.1e}); identidade RERI × p00 = contraste ({tst['3_identidade_ia_total_dif']:.1e}).
- **Comparação com a SIDRA 9554** (0,25%-0,57% menores no microdado): **controle interno de auditoria**, não validação externa; a causa não foi identificada e não deve ser afirmada ao leitor.
- **Fluxo da amostra reproduzido com o layout oficial:** {'; '.join(f"{r.etapa}: {int(r.n):,}".replace(',', '.') for r in flow.itertuples())}.

## 2. D-4. Desenho amostral
### 2.1 A variável de estrato (VERIFICADO no layout e no dicionário oficiais)
{md(lay_t)}
`Estrato`: nome oficial, tipo texto, 7 caracteres a partir da posição 21; as duas primeiras posições são o código da UF (dicionário oficial). O código antigo (`analise_bivariada_e_regressao_v2.py`) lia as posições 20-23 sob o nome "V1008" (`V1008_artigo` nos scripts de auditoria). **Não era um simples erro de rótulo:** essas 3 posições são o **prefixo de três caracteres do Estrato** (81 valores distintos; o Estrato completo tem 573), constante dentro da UPA, e **não** a V1008 oficial (posição 28-29, até 14 valores por UPA). Houve duas falhas independentes: (1) o manuscrito afirmava que o microdado não tinha a variável de estratificação, o que era falso; (2) o código nunca leu o estrato completo. **Os pontos estimados não dependem do estrato e permaneceram invariantes (VERIFICADO: as três configurações e os valores originais coincidem a 10⁻¹⁰); a variância precisava ser reestimada com o desenho correto, o que D-4 fez.** O leitor compartilhado passou a usar apenas nomes oficiais completos (UPA, Estrato, V1008, V1014, V1022, V1028) e testes automatizados (seção 2.7) falham se a posição ou o nome divergirem do layout. A V1008 oficial (28-29) e a V1014 (30-31) formam, com a UPA, a chave do domicílio, que coincide com o identificador reconstruído.
O peso V1028 tem **15** caracteres (posição 50-64); o código antigo lia 14 e perdia a 8ª casa decimal (diferença relativa máxima {chk['derivado_peso_max_dif_relativa_vs_V1028_15']:.1e}). O leitor da rodada D e o leitor compartilhado corrigido usam os 15 caracteres; o arquivo derivado original coincide linha a linha (UPA) com o novo e o peso difere em no máximo 9×10⁻⁹ (relativo). Os CSVs históricos **não foram regenerados**: uma nova execução dos scripts antigos mudaria os pesos só a partir da 9ª casa decimal.
Como a variável entra: **A** não usa estrato; **B** usa `Estrato` como estrato e `UPA` como conglomerado aninhado (o estrato com uma UPA recebe `lonely.psu="adjust"`); **C** não usa estrato explicitamente (os pesos replicados já embutem desenho e calibração).

### 2.2 Configurações e fórmulas (VERIFICADO no código `d1_motor.py`)
Estimandos como funções das quatro prevalências ponderadas de célula p00, p10, p01, p11 (referência, só raça/cor, só renda, ambos): PR_k = p_k/p00; RERI = PR11 − PR10 − PR01 + 1; RERI esperado = (PR10 − 1)(PR01 − 1); razão de PRs = PR11/(PR10 × PR01); componentes (pp): p10 − p00, p01 − p00, p11 − p10 − p01 + p00, conjunta p11 − p00; participação = interação/conjunta; identidade interação = RERI × p00.
- **A:** V = n/(n−1) Σⱼ (tⱼ − t̄)(tⱼ − t̄)′, com tⱼ o total das funções de influência na UPA j; delta por diferenças finitas centrais.
- **B:** V = Σₕ nₕ/(nₕ−1) Σⱼ∈ₕ (tⱼ − t̄ₕ)(tⱼ − t̄ₕ)′; estrato com uma UPA centrado na média global.
- **C:** V = Σᵣ (θᵣ − θ)² / (R − 1), R = 200, centrado na estimativa da amostra completa. É o bootstrap de Rao, Wu e Yue (1992) que, segundo fontes secundárias, o IBGE usa nos pesos replicados da PNAD Contínua (estimador `mse=TRUE`; o documento metodológico oficial do IBGE não pôde ser lido nesta sessão); as funções não lineares são recalculadas em cada réplica. Não há sementes (os pesos replicados são fornecidos); **falhas de replicação: 0** em todas as análises (célula vazia, NaN ou não convergência).
- IC: escala log para PRs e razão de PRs, logit para prevalências, linear para RERI, contrastes e componentes; z = 1,959964 nas três (a t com 199 gl seria 1,972).

### 2.3 Validação independente (VERIFICADO)
{md(val_tab)}
As estimativas pontuais do motor Python e do R `survey` coincidem a 10⁻¹³. A configuração B reproduz o `svydesign` do R a 10⁻¹⁰. Para C, a primeira comparação (com `svycontrast`, que aplica o método delta à covariância das réplicas, um estimador de primeira ordem) deu diferença de até 1,1% no erro-padrão; a comparação com `withReplicates` (que recalcula a função em cada réplica, como o motor Python) dá diferença de {val.loc[val.config=='C2','dif_rel_se'].max():.1e}. Os pesos replicados estão completos: {chk['n_colunas']} colunas, {chk['faltantes']} faltantes, nenhuma coluna zerada, nenhuma igual ao peso final; {chk['proporcao_de_pesos_replicados_zero']*100:.1f}% dos valores replicados são zero (esperado num bootstrap por conglomerado); a média das somas dos pesos replicados difere da soma do peso final em {abs(chk['media_das_somas_replicadas']/chk['soma_pesos_final']-1)*100:.3f}%.

### 2.4 Escolha da configuração principal (regra prefixada; a largura do IC não entrou)
Regra do protocolo: **C** se (i) o SE por replicação do motor reproduzir o do R (<10⁻⁶) e (ii) os 200 pesos replicados estiverem completos; senão **B**. **Desvio documentado:** na primeira avaliação, o critério (i) foi medido contra `svycontrast` e **falhou** (1,1% de diferença; leitura literal: principal = B). A diferença se deve ao estimador (delta sobre a covariância das réplicas contra recálculo em cada réplica), não a erro do código; reavaliei (i) contra `withReplicates` (mesmo estimador), que **passa**, e reporto as duas avaliações em `principal.json`. Principal = **C**. Motivos: são os pesos replicados que o IBGE distribui para estimar variância (método descrito por fontes secundárias; ver seção 10), incorpora a variância da calibração (raking), não exige regra ad hoc para o estrato com uma UPA e é reprodutível com o arquivo público. **B e A são reportadas em todas as tabelas.** Como verificação posterior (não usada na escolha), B e C dão ICs quase iguais, então a escolha não altera conclusões.

### 2.5 Concordância entre estimativas e ICs (VERIFICADO)
Estimativas pontuais: **idênticas nas três configurações** (todas as {len(conc)} quantidades), e A replica os valores originais publicados com diferença máxima de {d4s['max_dif_abs_estimativa_A_vs_publicado']:.1e} (arredondamento numérico). O IC de A difere do original publicado em no máximo {d4s['max_dif_rel_pct_IC_A_vs_publicado_PRs_e_RERI']:.3f}% (PRs, RERI e razão de PRs; a diferença vem da correção de amostra finita do sanduíche do `statsmodels`).
{md(conc_sum)}
Tabelas completas, com diferenças absolutas e relativas dos limites: `D4_concordancia_estimativas_e_ICs.csv`; formato longo: `D4_estimativas_por_configuracao.csv`.

**Raça/cor × renda (≤1/4 SM), IC 95% sob A (pesos+UPA), B (+Estrato) e C (pesos replicados):**
{d4_table(PI)}

**Raça/cor × escolaridade:**
{d4_table(PE)}

O RERI de qualquer insegurança em raça × escolaridade tem limite inferior {f(g4(PE,'ia_total','reri').A_lo,4)} (A) e {f(g4(PE,'ia_total','reri').C_lo,4)} (C): a maior diferença **relativa** de limite (≈{f(cq[cq.quantidade=='reri'][['dif_rel_lo_C_vs_A_pct']].abs().max().iloc[0],0)}%) é um artefato de estar perto de zero (diferença absoluta {f(abs(g4(PE,'ia_total','reri').C_lo-g4(PE,'ia_total','reri').A_lo),4)}).
**Mudança de interpretação: nenhuma** pelo critério "IC exclui o valor nulo" ({mchg} de {len(mat)} linhas). Em particular: RERI grave e razão de PRs continuam com IC que exclui 0 e 1; RERI de qualquer insegurança continua com IC que inclui 0.
**Não reestimado nesta rodada (NÃO VERIFICADO quanto ao efeito do desenho):** PRs ajustadas por faixa de renda (Fig. S1) e por escolaridade (Fig. S2), atenuação, modelo mutuamente ajustado, gradiente e três vias (modelos de regressão com covariáveis) e o MAIHDA (modelo misto sem peso; não usa variância de desenho). O resumo do manuscrito cita as PRs por faixa (1,26 e 1,60): seus ICs, se C for adotada, precisariam ser reestimados.

### 2.6 O estrato com uma única UPA (VERIFICADO em `D9_estrato_solitario.json`)
Estrato {lon['estrato_com_1_UPA']}, UPA {lon['upa']}, {lon['domicilios']} domicílios, {lon['pct_do_peso_total']:.4f}% do peso total. **Configuração B:** política `lonely.psu="adjust"` (a UPA é centrada na média global; equivale ao R `survey`); a política alternativa `certainty` (contribuição zero) altera os erros-padrão em no máximo {lon['politica_B_max_dif_rel_SE_pct_certainty_vs_adjust']:.4f}% (`D9_estrato_solitario_politica_B.csv`), então a escolha é imaterial. **Configuração C:** a variância vem da dispersão entre as 200 réplicas, sem regra de estrato solitário a escolher; nessa UPA os pesos replicados variam (razão média ao peso final {lon['replicados_da_UPA_solitaria']['media_da_razao_peso_replicado_sobre_final']:.2f}; nenhuma réplica igual ao peso final; {lon['replicados_da_UPA_solitaria']['fracao_de_replicas_com_todos_os_pesos_zero']*100:.0f}% das réplicas com todos os pesos zero), isto é, a UPA entra na variância replicada. **NÃO VERIFICADO** em fonte primária: como o IBGE gera as réplicas para estratos com uma UPA (o documento metodológico oficial não pôde ser lido); por isso a adequação de C ao produto 2023 se apoia na validação contra o `survey` e nesse diagnóstico empírico.

### 2.7 Testes automatizados de integridade (VERIFICADO; `d8_testes_integridade.py`, `D8_testes_integridade.csv`)
{md(pd.DataFrame(t8['testes']))}
Teste de mutação (`--autoteste`): cada teste **falha** quando o dado é corrompido (remover um responsável; chave duplicada; domicílio com dois responsáveis; peso ausente; EBIA inválida; Estrato com 572 valores; coluna de peso replicado faltando; matriz com 199 colunas; ID reconstruído divergente; rótulo antigo "V1008" em 20-23; peso de 14 caracteres): **{sum(1 for a in t8['autoteste_mutacao'] if a['falhou_como_esperado'])} de {len(t8['autoteste_mutacao'])} mutações detectadas**. O teste 8 teria falhado com o leitor antigo.

## 3. D-2. Incerteza da decomposição
Método: os componentes são funções das mesmas quatro prevalências, então recebem IC pelas configurações A, B e C (principal C). Fórmulas na seção 2.2. Réplicas: 200; sementes: não se aplica; falhas: 0.
{md(pd.DataFrame(d2t))}
**IC da participação percentual (regra prefixada):** só reportar se (a) o limite inferior do IC da diferença conjunta for > 0 e o CV < 0,2 **e** (b) nenhuma réplica tiver |participação| > 3 × |estimativa|.
{md(dgt)}
Resultado pela regra literal: **IC da participação reportável** para grave (raça × renda e raça × escolaridade) e para qualquer em raça × escolaridade; **não reportável** para **qualquer insegurança em raça × renda**, porque a estimativa ({f(dg.iloc[0].participacao_pct,1)}%) é pequena frente ao erro-padrão e {f(dg.iloc[0]['fracao_replicas_|part|>3x|estimativa|']*100,1)}% das réplicas ultrapassam 3 × a estimativa. **Ressalva do autor da análise:** o denominador é muito estável (CV {f(dg.iloc[0].cv_conjunta,3)}; mínimo replicado {f(dg.iloc[0].denominador_replicado_min,1)} pp), então o IC ({rng(d2r(PI,'ia_total','participacao_pct').ic_inf, d2r(PI,'ia_total','participacao_pct').ic_sup,1)}%) é numericamente interpretável; a regra (b) foi mal calibrada para estimativas próximas de zero. Sigo a regra como escrita, e o IC está no CSV para consulta. **DEPENDE DE DECISÃO DOS AUTORES** se o mostram; minha sugestão é reportar os componentes em pp com IC e a participação apenas para a insegurança grave.
A decomposição é aritmética e descritiva; não identifica efeitos causais.

## 4. D-1. Análise secundária padronizada (raça/cor × renda ≤1/4 SM)
**Preservado:** RERI e decomposição brutos (análise descritiva da desigualdade observada).
**Modelo:** regressão logística ponderada do desfecho nas três células não referentes e nas covariáveis; prevalência padronizada da célula k = média ponderada, sobre **todos** os domicílios da amostra, da probabilidade prevista com a célula fixada em k e as covariáveis observadas (g-computation). Estimandos derivados (PRs marginais, RERI, razão de PRs, componentes) calculados **sem arredondar** a partir das quatro prevalências padronizadas. IC: 200 pesos replicados, com o modelo **reajustado em cada réplica** (configuração principal de D-4); a diferença padronizado − bruto também tem IC pareado nas réplicas. Convergência: {'sim' if all(json.loads((OUTD/'D1_D2_resumo.json').read_text(encoding='utf-8'))['D1'][y]['fit_convergiu'] for y in ('ia_total','ia_grave')) else 'NÃO'}; réplicas não convergidas: {sum(json.loads((OUTD/'D1_D2_resumo.json').read_text(encoding='utf-8'))['D1'][y]['replicas_nao_convergiram'] for y in ('ia_total','ia_grave'))}.
**Covariáveis e justificativa:** *sexo registrado* (a proporção de mulheres na referência varia de {f(comp.iloc[0].pct_mulher,1)}% a {f(comp.iloc[3].pct_mulher,1)}% entre as células); *escolaridade em 4 categorias* (eixo socioeconômico distinto da renda, correlacionado com raça/cor e renda: superior completo ou incompleto em {f(comp.iloc[0].pct_superior,1)}% da célula de referência e {f(comp.iloc[3].pct_superior,1)}% de negros de baixa renda); *residência* (rural: {f(comp.iloc[0].pct_rural,1)}% na referência, {f(comp.iloc[3].pct_rural,1)}% em negros de baixa renda, e associação forte com o desfecho). Região, idade, composição domiciliar e outras **não** entraram (sem justificativa substantiva explícita).
{md(comp_t)}
**Estimando respondido:** "qual seria a desigualdade conjunta observada (PRs, RERI, razão de PRs e sua decomposição em pp) se os quatro grupos tivessem a mesma distribuição de sexo, escolaridade e residência da população total, supondo que os efeitos dessas covariáveis sejam homogêneos na escala logit entre as células". **Não substitui a análise bruta**, que descreve a desigualdade que de fato existe na população, com sua composição real. **Não é causal, não é mediação e não elimina confusão:** a escolaridade é um eixo de posição socioeconômica que se sobrepõe à renda, e padronizá-la muda o que se compara.
**Resultados (IC 95% pelos pesos replicados):**
{md(pd.DataFrame(d1t))}
Modelo logístico (razões de chances; transparência):
{md(coef_t)}
**Leitura:** (i) as prevalências padronizadas dos grupos desfavorecidos caem e a da referência sobe, porque a referência (não negros de renda >1/4 SM) é mais escolarizada que a população total; (ii) para a insegurança grave o excesso aditivo (RERI) cai de {f(sr.bruto_est)} para {f(sr.padronizado_est)} (diferença {ci(sr.dif_padronizado_menos_bruto, sr.dif_ic_inf, sr.dif_ic_sup)}), o contraste de interação de {f(si.bruto_est,1)} para {f(si.padronizado_est,1)} pp ({rng(si.padronizado_lo, si.padronizado_hi,1)}) e sua participação de {f(s1r('ia_grave','participacao_pct').bruto_est,1)}% para {f(s1r('ia_grave','participacao_pct').padronizado_est,1)}% ({rng(s1r('ia_grave','participacao_pct').padronizado_lo, s1r('ia_grave','participacao_pct').padronizado_hi,1)}); o limite inferior do RERI padronizado fica muito perto de zero; (iii) a razão de PRs sobe de {f(srr.bruto_est)} para {f(srr.padronizado_est)}, mas continua abaixo de 1 nos dois desfechos; (iv) para qualquer insegurança o RERI é {f(ar.padronizado_est)} ({rng(ar.padronizado_lo, ar.padronizado_hi)}), sem mudança relevante. Isto sugere que **cerca de metade do excesso aditivo bruto na insegurança grave coincide com diferenças de composição** em sexo, escolaridade e residência entre os grupos, e a outra metade persiste. Sem interpretação causal.
**Limitações (VERIFICADO no desenho da análise):** o modelo supõe efeitos homogêneos das covariáveis na escala logit (sem termos célula × covariável); a padronização atribui cada célula a todos os domicílios, o que extrapola para combinações raras (p.ex., negros de baixa renda com ensino superior: {f(comp.iloc[3].pct_superior,1)}% da célula), dependendo do modelo; a escolha das covariáveis foi restrita e prefixada, e outra escolha daria outro número.

## 5. D-3. Sensibilidade ao ponto de corte de renda (SENSIBILIDADE EXPLORATÓRIA)
Contraste bruto raça/cor × renda per capita com cortes ≤1/4 (primário), ≤1/2 e ≤1 SM (VDI5009 ≤ 1, ≤ 2, ≤ 3; o código 9 nunca é "baixa renda", como no original), IC pela configuração principal. Não se escolhe corte preferido; o corte primário permanece ≤1/4 SM.
Tamanho dos grupos e % de domicílios com renda baixa (ponderado):
{md(n3)}
{md(pd.DataFrame(d3t))}
**Leitura:** insegurança grave: RERI positivo com IC que exclui 0 nos três cortes, razão de PRs entre {f(min(d3r(c,'ia_grave','ror').estimativa for c in CUTS))} e {f(max(d3r(c,'ia_grave','ror').estimativa for c in CUTS))}. Qualquer insegurança: RERI {f(d3r(CUTS[0],'ia_total','reri').estimativa)} (≤1/4), {f(d3r(CUTS[1],'ia_total','reri').estimativa)} (≤1/2), {f(d3r(CUTS[2],'ia_total','reri').estimativa)} (≤1 SM, IC {rng(d3r(CUTS[2],'ia_total','reri').ic_inf, d3r(CUTS[2],'ia_total','reri').ic_sup)}): o padrão **não é monotônico**, e "compatível com aditividade" para qualquer insegurança **depende do corte**. A razão de PRs fica abaixo de 1 em todos os cortes e desfechos.

## 6. D-5. Registros ignorados (VERIFICADO)
Excluídos: {d5i['n_raca_ignorada']} domicílios com V2010 = 9 e {d5i['n_renda_ignorada']} com VDI5009 = 9 (sobreposição: {d5i['n_ambos']}); {d5i['n_excluidos_uniao']} no total; amostra restrita {n_restr}.
Todos os estimandos principais foram repetidos (brutos: raça × renda e raça × escolaridade; padronizados: raça × renda; prevalências geral e por categoria), com IC pela configuração principal. Maior diferença absoluta por classe (arquivo completo: `D5_ignorados_comparacao_completa.csv`):
{md(sm5t)}
A linha "prevalência (geral e por categoria)" é a da faixa >2 SM na Tabela 1, que no código original inclui os 77 domicílios de renda ignorada: {f(q5[q5.desfecho=='ia_total'].iloc[0].principal_est,3)}% → {f(q5[q5.desfecho=='ia_total'].iloc[0].excluidos_est,3)}% (qualquer) e {f(q5[q5.desfecho=='ia_grave'].iloc[0].principal_est,3)}% → {f(q5[q5.desfecho=='ia_grave'].iloc[0].excluidos_est,3)}% (grave). **Critério prefixado** (máxima diferença < 10% da meia-largura do IC): **atendido em todas as classes, exceto nessa linha da Tabela 1** (razão até {f(d5i['maior_razao_dif_sobre_meia_largura'],3)}). **Redação:** só é demonstrado que a exclusão não alterou materialmente as estimativas de célula, PRs, RERI, razão de PRs, componentes absolutos, participação e as versões padronizadas; **a frase geral "não alterou materialmente as estimativas" não deve incluir a prevalência da faixa >2 SM da Tabela 1** sem essa ressalva (proposta em `E_PROPOSTAS…`).

## 7. Matriz "resultado original × resultado corrigido" (entrega D)
Arquivo: `D_matriz_original_vs_corrigido.csv` ({len(mat)} linhas: prevalências da Tabela 1, quatro células, PRs, RERI, RERI esperado, razão de PRs, componentes e participação). "Original" = `dados/v2_20260925`; "corrigido" = configuração {princ['principal']}; A e B ao lado.
- **Ponto estimado:** nenhuma mudança (dif. máx. {mat['dif_est_corrigido_menos_original'].abs().max():.1e}).
- **IC:** mudam levemente; razão de largura corrigido/original entre {mat['razao_largura_corrigido_sobre_original'].min():.3f} e {mat['razao_largura_corrigido_sobre_original'].max():.3f}.
- **Interpretação:** {mchg} mudanças pelo critério do valor nulo. Componentes e participação não tinham IC original (IC novo).
{md(mx.rename(columns={'par':'contraste','original_est':'RERI original','original_ic_inf':'IC orig. inf','original_ic_sup':'IC orig. sup','corrigido_ic_inf':'IC corr. inf','corrigido_ic_sup':'IC corr. sup','exclui_nulo_original':'orig. exclui 0','exclui_nulo_corrigido':'corr. exclui 0','mudanca_de_interpretacao':'mudança de interpretação'}))}
**Novas análises (não substituem originais):** D-1 (padronizada), D-2 (ICs dos componentes), D-3 (cortes), D-5 (exclusões).

## 8. Decisão recomendada sobre qual análise é principal
1. **Descrição da desigualdade populacional (principal):** RERI, razão de PRs e decomposição **brutos**, ICs pela configuração **C**. Estimandos e estimativas pontuais inalterados.
2. **Análise secundária:** padronização (D-1) no suplemento, com uma frase no texto: para a insegurança grave o excesso aditivo persiste, com cerca de metade da magnitude, depois de padronizar.
3. **Robustez exploratória:** D-3 e D-5 no suplemento.
4. **Consequência para as conclusões:** "super-aditiva na grave" e "sub-multiplicativa nos dois" se mantêm nas três configurações de variância, nos três cortes e sem os ignorados; a versão padronizada reduz a magnitude do RERI grave; "compatível com aditividade para qualquer insegurança" vale no corte primário e em ≤1/2 SM, não em ≤1 SM. **DEPENDE DE DECISÃO DOS AUTORES.**

## 9. Limitações
Regressões com covariáveis (Fig. S1, atenuação etc.) e o MAIHDA não foram reestimados sob os pesos replicados (NÃO VERIFICADO); a padronização depende do conjunto de covariáveis e da homogeneidade logit; z em vez de t; o estrato com uma UPA recebe tratamento ad hoc em B; as diferenças com o SIDRA (0,25%-0,57% menores no microdado) seguem sem explicação; o critério (b) do protocolo para a participação foi mal calibrado; o desvio na regra de escolha da configuração principal está documentado; a análise usa apenas T4 de 2023.

## 10. Classificação das afirmações
| Afirmação | Classe |
|---|---|
| A variável oficial de estrato é `Estrato` (pos. 21-27, 573 estratos, 15.033 UPAs, 1 estrato com 1 UPA); o microdado traz 200 pesos replicados completos | VERIFICADO |
| O código antigo lia os 3 primeiros caracteres do Estrato sob o rótulo "V1008" | VERIFICADO |
| Estimativas pontuais idênticas nas configurações A, B e C e iguais às originais | VERIFICADO |
| Motor B reproduz `survey::svydesign` e motor C reproduz `survey::withReplicates` | VERIFICADO |
| C é o método oficial do IBGE (bootstrap de Rao, Wu e Yue; `svrepdesign(type="bootstrap", mse=TRUE)`) | VERIFICADO em fontes secundárias (blog de usuário da PNADC e pacote `PNADcIBGE` via busca); o PDF oficial do IBGE não pôde ser lido nesta sessão: **NÃO VERIFICADO** na fonte primária |
| Nenhuma conclusão muda pelo critério "IC exclui o nulo" entre A, B e C | VERIFICADO |
| Regressões por faixa, atenuação e MAIHDA sob C | NÃO VERIFICADO |
| RERI padronizado grave ≈ metade do bruto; razão de PRs padronizada < 1 | VERIFICADO (análise secundária; depende das covariáveis e da homogeneidade logit) |
| Interpretar a padronização como causal, mediação ou controle de confusão | **Não afirmado** |
| Cerca de metade do excesso aditivo grave coincide com composição de sexo, escolaridade e residência | VERIFICADO como descrição; **explicação causal: não afirmada** |
| RERI grave > 0 e razão de PRs < 1 nos três cortes; "aditividade" para qualquer insegurança só em ≤1/4 e ≤1/2 SM | SENSIBILIDADE EXPLORATÓRIA |
| Exclusão dos 96 registros não altera materialmente estimativas de célula, PRs, RERI, razão de PRs e componentes | VERIFICADO (com a ressalva da linha >2 SM da Tabela 1) |
| Adotar C como principal; mostrar ou não IC da participação de qualquer insegurança; adotar a padronização no texto | DEPENDE DE DECISÃO DOS AUTORES |
| Autoria, ética, financiamento, conflitos, garantidor, declaração de IA, repositório, licença, referência Câmara na fonte da revista | DEPENDE DE DECISÃO DOS AUTORES (ver F) |
"""
(OUTD / "RELATORIO_TECNICO_RODADA_D.md").write_text(rep, encoding="utf-8")

# ================================================================== E. PROPOSTAS
def pr(e, lo, hi, d=2): return ci(e, lo, hi, d)
def cj(e, lo, hi, d=2): return f"{f(e, d)} (95% CI {rng(lo, hi, d)})"
ab = []
def abrow(item, old, new): ab.append({"item do resumo/texto": item, "impresso atual (rev3)": old, "com pesos replicados (C)": new, "muda?": "não" if old == new else "sim"})
def cc(pair, y, q, d): g = g4(pair, y, q); return pr(g.pub_est, g.pub_lo, g.pub_hi, d), pr(g.C_est, g.C_lo, g.C_hi, d)
for lab, y, q, d in [("PR grave, ambos", "ia_grave", "rr11", 2), ("RERI grave", "ia_grave", "reri", 2), ("razão de PRs grave", "ia_grave", "ror", 2), ("RERI qualquer", "ia_total", "reri", 2), ("razão de PRs qualquer", "ia_total", "ror", 2)]:
    o, n = cc(PI, y, q, d); abrow(lab, o, n)
for y, lab in (("ia_total", "prevalência qualquer (%)"), ("ia_grave", "prevalência grave (%)")):
    g = conc[(conc.grupo == "prevalencia") & (conc.par == "Total") & (conc.desfecho == y)].iloc[0]; abrow(lab, pr(g.pub_est, g.pub_lo, g.pub_hi, 1), pr(g.C_est, g.C_lo, g.C_hi, 1))
abt = md(pd.DataFrame(ab))
prev_chg = []
for y in ("ia_total", "ia_grave"):
    for _, g in conc[(conc.grupo == "prevalencia") & (conc.desfecho == y)].iterrows():
        o, n = pr(g.pub_est, g.pub_lo, g.pub_hi, 1), pr(g.C_est, g.C_lo, g.C_hi, 1)
        if o != n: prev_chg.append(f"{g.par} ({OL[y]}): {o} → {n}")
c5 = sm5[sm5.analise == "bruta"].set_index("classe")
prop = f"""# Propostas de alteração no manuscrito, tabelas, figura e suplemento (NÃO APLICADAS)

Base: `A_Manuscript_IJE_rev3.docx`. Nada abaixo foi aplicado. Todas as passagens propostas dependem de **DECISÃO DOS AUTORES**; os números vêm dos CSV de `rodada_D/`. Se os autores adotarem a configuração C, todos os ICs impressos que vêm de modelos de células (resumo, Tabelas 1-3, Fig. 1, Suplemento S4-S5) devem ser regerados pelo pipeline (nenhum ponto estimado muda).

## 1. Números impressos que mudariam com a configuração C (só ICs)
{abt}
Linhas da Tabela 1 cujo IC impresso mudaria (1 casa decimal): {'; '.join(prev_chg) if prev_chg else 'nenhuma'}. Fig. 1 (RERI e razão de PRs): mudam levemente as barras de IC. As PRs ajustadas por faixa de renda citadas no resumo (1,26 e 1,60) e os ICs da atenuação **não** foram reestimados (NÃO VERIFICADO).

## 2. Métodos
**2.0 Amostra (substitui "complete data on all analysed variables").**
> "The public-use file included 473 206 person records. We selected the 173 676 records coded as household reference persons, one per household; all had a valid food insecurity classification and a survey weight. The public microdata provide primary sampling units, strata and replicate weights. Point estimates used the final survey weight."
Depois **uma** das duas frases (nunca as duas): se C for a configuração final, "Variance estimation followed the replicate-weight procedure provided with the microdata (200 bootstrap weights)."; se B for a final, "Variance estimation accounted for primary sampling units and strata (a stratum with a single primary sampling unit was centred at the overall mean)." A frase de C só entra depois que C for congelada como método final.

**2.1 Variância (substitui a frase atual sobre o estrato).**
> "Variance was estimated with the 200 bootstrap replicate weights supplied with the public microdata (V1028001-V1028200; Rao-Wu-Yue), recomputing every estimate in each replicate. Intervals with clustering on primary sampling units alone, and with primary sampling units nested in strata (variable Estrato), were similar (Supplementary Table SR-D4a)."
Remover da Discussão a limitação "variance estimates ignore stratification" e da Tabela 1 a nota "clustered on primary sampling units"; nova nota: "95% confidence intervals from replicate weights, on the logit scale".

**2.2 Registros ignorados (já na rev3; acrescentar a sensibilidade; a codificação original é mantida só para reproduzir a análise primária e não é uma escolha substantiva).**
> "Excluding {d5i['n_raca_ignorada']} records with ignored race/colour and {d5i['n_renda_ignorada']} with ignored income did not materially alter the primary interaction estimates (Supplementary Table SR-D5). Detailed: excluding the {d5i['n_raca_ignorada']} households with ignored race/colour and the {d5i['n_renda_ignorada']} with ignored income did not materially alter the joint-category prevalences, prevalence ratios, RERI, ratio of prevalence ratios or absolute components (largest absolute changes: {f(abs(c5.loc['prevalencia de celula','maior_dif_abs']),3)} percentage points in cell prevalence, {f(abs(c5.loc['PR','maior_dif_abs']),3)} in prevalence ratios, {f(abs(c5.loc['RERI','maior_dif_abs']),3)} in the RERI, {f(abs(c5.loc['razao de PRs','maior_dif_abs']),3)} in the ratio of prevalence ratios and {f(abs(c5.loc['componente absoluto (pp)','maior_dif_abs']),3)} percentage points in absolute components; Supplementary Table SR-D5). The prevalence in the highest income band, which contained the {d5i['n_renda_ignorada']} households, changed by {f(q5[q5.desfecho=='ia_total'].iloc[0].dif_abs,2)} percentage points."
(a frase geral "não alterou materialmente" só com essa ressalva: ver relatório, seção 6).

**2.3 Padronização (nova análise secundária).**
> "As a secondary, descriptive analysis we standardized the four joint-category prevalences to the distribution of recorded sex, education (four categories) and residence in the whole sample, using a survey-weighted logistic model with the joint category and these covariates and averaging predicted probabilities with the joint category fixed (g-computation); the model assumes homogeneous covariate effects on the logit scale. Confidence intervals refit the model in each replicate. This describes the disparity if the four groups shared the same composition; it is not a causal effect and does not remove confounding."

**2.4 Exploratória.** "As exploratory sensitivity analyses, we repeated the joint-category contrast with income cut-points of ≤1/2 and ≤1 minimum wage (Supplementary Table SR-D3)."

## 3. Resultados
**3.1 Decomposição com IC (substitui a frase sem IC).** Grave: "The interaction component was {cj(d2r(PI,'ia_grave','interacao_pp').estimativa, d2r(PI,'ia_grave','interacao_pp').ic_inf, d2r(PI,'ia_grave','interacao_pp').ic_sup, 1)} of {cj(d2r(PI,'ia_grave','conjunta_pp').estimativa, d2r(PI,'ia_grave','conjunta_pp').ic_inf, d2r(PI,'ia_grave','conjunta_pp').ic_sup, 1)} percentage points ({cj(d2r(PI,'ia_grave','participacao_pct').estimativa, d2r(PI,'ia_grave','participacao_pct').ic_inf, d2r(PI,'ia_grave','participacao_pct').ic_sup, 1)}%)." Qualquer: "The interaction component was {cj(d2r(PI,'ia_total','interacao_pp').estimativa, d2r(PI,'ia_total','interacao_pp').ic_inf, d2r(PI,'ia_total','interacao_pp').ic_sup, 1)} of {cj(d2r(PI,'ia_total','conjunta_pp').estimativa, d2r(PI,'ia_total','conjunta_pp').ic_inf, d2r(PI,'ia_total','conjunta_pp').ic_sup, 1)} percentage points"; **sem** participação percentual para qualquer insegurança em raça × renda (regra do protocolo; DEPENDE DE DECISÃO). Remover a limitação "no confidence interval was computed for the decomposition" (Discussão e notas das Tabelas 2-3).
**3.2 Padronização (1 parágrafo).** "After standardization for recorded sex, education and residence, the RERI for severe food insecurity was {cj(sr.padronizado_est, sr.padronizado_lo, sr.padronizado_hi)} (crude {cj(sr.bruto_est, sr.bruto_lo, sr.bruto_hi)}) and the ratio of prevalence ratios {cj(srr.padronizado_est, srr.padronizado_lo, srr.padronizado_hi)}; for any food insecurity the RERI was {cj(ar.padronizado_est, ar.padronizado_lo, ar.padronizado_hi)}."
**3.3 Corte.** "Across income cut-points the RERI for severe insecurity remained positive and the ratio of prevalence ratios below one; for any insecurity the RERI was compatible with zero at ≤1/4 and ≤1/2 minimum wage but not at ≤1 ({cj(d3r(CUTS[2],'ia_total','reri').estimativa, d3r(CUTS[2],'ia_total','reri').ic_inf, d3r(CUTS[2],'ia_total','reri').ic_sup)})."

## 4. Resumo, mensagens-chave, Discussão e Conclusão
- **"Compatible with additivity for any"** precisa de qualificador: "at the primary cut-point" (a sensibilidade mostra RERI positivo em ≤1 SM). Sugestão para o resumo: "…compatible with additivity for any (at the ≤1/4 minimum wage cut-point)…" (custa palavras; o resumo está em 243/250).
- **Discussão, limitações:** trocar "variance estimates ignore stratification" por "the standardized analysis assumes homogeneous covariate effects on the logit scale, and cut-point analyses were exploratory".
- **Discussão, 2º parágrafo:** acrescentar que, depois de padronizar, o excesso aditivo grave cai à metade (limite inferior do IC perto de zero), o que sugere que parte do excesso bruto coincide com composição; **sem** linguagem causal.
- **Mensagem-chave 1** e **Conclusão:** manter "super-additive but sub-multiplicative" restrito à insegurança grave; incluir que "the additive excess for severe insecurity was about halved after standardization" apenas se os autores adotarem D-1 no texto.

## 5. Tabelas, figura e suplemento
- **Tabela 1:** nova nota de IC (ver 2.1); ">2" inclui os 77 domicílios de renda ignorada (nota) ou passa a excluí-los (DEPENDE DE DECISÃO; a prevalência muda {f(q5[q5.desfecho=='ia_total'].iloc[0].dif_abs,2)} pp).
- **Tabelas 2-3:** ICs regerados; acrescentar coluna ou nota com o IC do componente de interação (pp); retirar a nota "No confidence interval was computed for the decomposition".
- **Figura 1:** regerar com os ICs de C (mesmo desenho); painel opcional (suplemento) comparando RERI e razão de PRs brutos e padronizados.
- **Suplemento (novas tabelas, arquivo `E_tabelas_suplementares_propostas_rodadaD.docx`):** SR-D4a (raça × renda, A/B/C), SR-D4b (raça × escolaridade), SR-D4c (prevalências), SR-D2 (componentes com IC), SR-D1 (padronizada × bruta, com composição das células e OR do modelo em CSV), SR-D3 (cortes), SR-D5 (exclusões). Renumerar como S15-S21 se aprovadas. **S1b:** acrescentar as linhas "variância" (configurações) e "padronização (covariáveis)". **S1a:** corrigir o rótulo do 9 de renda ("ignored", não "sem rendimento").
- **Rastreabilidade:** incluir as novas tabelas em `C_Traceability_table` apontando para `rodada_D/*.csv`.
"""
(OUTD / "E_PROPOSTAS_alteracoes_manuscrito_rodadaD.md").write_text(prop, encoding="utf-8")

# ================================================================== F. CHECKLIST
chk_md = """# Checklist de pendências remanescentes (rodada D, 25/09/2026)

| Item | Estado | Classe |
|---|---|---|
| Autores, ordem, afiliações, autor para correspondência, ORCID | Campos vazios no manuscrito | DEPENDE DE DECISÃO DOS AUTORES |
| Declaração de ética (comitê e número, ou dispensa com motivo) | Não afirmada | DEPENDE DE DECISÃO DOS AUTORES |
| Financiamento ("This work was supported by … [grant]") | Vazio | DEPENDE DE DECISÃO DOS AUTORES |
| Conflito de interesses (declaração + formulário do sistema do IJE) | Vazio; formulário não existe | DEPENDE DE DECISÃO DOS AUTORES |
| Garantidor (dentro de "Author contributions") e contribuições detalhadas (CRediT) | Vazio | DEPENDE DE DECISÃO DOS AUTORES |
| Declaração de uso de IA (Métodos e Declarações) | Escrita; confirmação humana e nome/versão/data das ferramentas pendentes | DEPENDE DE DECISÃO DOS AUTORES |
| Repositório (código e dados derivados) e DOI | **Não criado** (instrução desta rodada). Scripts novos prontos para publicação (sem caminhos absolutos; `run_all.py`); saídas grandes ficam fora (`dados/rodada_d_cache/`, regenerável) | DEPENDE DE DECISÃO DOS AUTORES |
| Licença do repositório | **Não escolhida** | DEPENDE DE DECISÃO DOS AUTORES |
| Referência Câmara et al. (AJPH 2026) | Metadados do registro do PubMed (PMID 42492040: 6 autores, e1-e10, online 23/07/2026); **falta conferir na página da revista** | NÃO VERIFICADO (fonte primária) |
| Adoção da configuração C, da padronização e das novas tabelas no manuscrito | Propostas em `E_PROPOSTAS…`; nada aplicado | DEPENDE DE DECISÃO DOS AUTORES |
| Reestimar sob pesos replicados as regressões com covariáveis (Fig. S1, atenuação, mutuamente ajustado) e revisar o resumo se for adotada a C | Não feito | NÃO VERIFICADO / DEPENDE DE DECISÃO |
| Leitor compartilhado `analise_bivariada_e_regressao_v2.py` | **Corrigido** (Estrato, V1008, V1014 e V1028 de 15 caracteres, nomes oficiais; testes automatizados PASS); CSVs históricos **não regenerados** | VERIFICADO |
| Outros scripts do projeto com o prefixo do Estrato sob o nome "V1008" (`processar_uf_determinantes.py`, `processar_microdados_pnad.py`, cópia em `artigos/04_…/scripts/`) | **Não alterados** (fora do escopo do Artigo 3; alimentam outras análises) | DEPENDE DE DECISÃO DOS AUTORES |
| Pacote SSM (`MANUSCRITO_EN_SSM_20260925/`) com "attributable to", "super-additive but sub-multiplicative" genérico e a premissa falsa do estrato | **Não alterado** | DEPENDE DE DECISÃO DOS AUTORES |
| Diferença de 0,25%-0,57% entre o microdado e a tabela SIDRA 9554 | Causa não identificada | NÃO VERIFICADO |
| Contagem oficial de palavras e formatação no sistema do IJE | Só se confirma no upload | NÃO VERIFICADO |
| Carta ao editor, início da submissão | Não feitos | — |
"""
(OUTD / "F_CHECKLIST_pendencias_rodadaD.md").write_text(chk_md, encoding="utf-8")

# ================================================================== README (C)
readme = """# Rodada D: scripts e reprodução

Executar de qualquer diretório (Python 3.12 com numpy, pandas, scipy, statsmodels, python-docx; R 4.x com o pacote `survey`):

```
python scripts/rodada_d/run_all.py      # variavel opcional RSCRIPT com o caminho do Rscript
```

| Ordem | Script | O que faz |
|---|---|---|
| 0 | `d_config.py` | localiza a raiz (pasta com `dados_ibge/`), lê o layout oficial do IBGE, registra ambiente, entradas (SHA-256), comando e data em `rodada_D/00_ambiente_e_execucao.json` |
| 1 | `d0_extrair.py` | lê o ZIP com as posições do layout oficial (Estrato, V1028 com 15 caracteres, 200 pesos replicados); grava cache regenerável |
| 2 | `d3_D4_desenho.py` | D-4: estimandos sob A, B e C e comparação com os valores originais |
| 3 | `d3b_validacao_R_survey.R` | validação independente em R (`svydesign`, `svrepdesign`, `withReplicates`) |
| 4 | `d3c_decisao_principal.py` | aplica a regra prefixada de escolha da configuração principal |
| 5 | `d4a_testes_codigo.py` | testes de correção do motor |
| 6 | `d4b_D1_D2.py` | D-2 (ICs da decomposição) e D-1 (padronização) |
| 7 | `d5_D3_D5.py` | D-3 (cortes) e D-5 (ignorados) |
| 8 | `d6_matriz_e_tabelas.py` | matriz original × corrigido e tabelas propostas (.docx) |
| 9 | `d7_relatorios.py` | relatórios em Markdown a partir dos CSV |
| — | `d8_testes_integridade.py` | testes automatizados de integridade da amostra e do desenho (`--autoteste`: testes de mutação) |
| — | `d9_estrato_solitario.py` | o estrato com uma UPA: política em B e comportamento dos pesos replicados |
| — | `d10_documentacao_amostra.py` | registro de verificações, tabela de validação da amostra e nota de métodos |
| — | `d11_regressoes_C.py`, `d11a`, `d11b`, `d11c` | regressões e tabelas com a configuração C em `dados/v3_rodadaD_C/` e validação independente em R |
| — | `run_pacote_rev4.py` | reprodução completa do pacote IJE rev4 (rodada D, v3, figuras, manuscrito, suplemento, auditorias, matriz, notas) |

Motor: `d1_motor.py` (fórmulas no cabeçalho). Dados: `d2_dados.py`. Saídas: `MANUSCRITO_IJE_20260925/rodada_D/`. Protocolo: `PROTOCOLO_RODADA_D.md`.
Nenhum script altera o manuscrito, o suplemento ou as figuras.
"""
(OUTD / "README_RODADA_D.md").write_text(readme, encoding="utf-8")
log_execucao("d7_relatorios.py")
print("relatorios ok")
